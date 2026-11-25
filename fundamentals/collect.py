"""Large-cap, five-year, incremental SEC fundamentals collector."""
import argparse
import os
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from pymongo import MongoClient,UpdateOne,ReplaceOne,ASCENDING
from .sec_client import SecClient
from .universe import select_universe,join_sec
from .normalize import normalize, diagnose_annual
from .sec_inventory import inventory
from .migrate import migrate_all
from .cik_sync import sec_map, normalize_ticker, resolve_issuer, cik10

def now(): return datetime.now(timezone.utc)
def aware(value):
    if value is None:return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
def due(state,refresh_days,force_refresh=False):
    if force_refresh:return True
    if not state:return True
    retry=aware(state.get('next_retry_at'))
    if retry and retry>now():return False
    last=aware(state.get('last_success_at'))
    return not last or last<=now()-timedelta(days=refresh_days)

def classify_periods(rows):
    """Classify normalized SEC coverage without inventing annual facts."""
    annual=sum(r.get('period_type')=='annual' for r in rows)
    quarterly=sum(r.get('period_type')=='quarterly' for r in rows)
    if annual:
        return 'success',annual,quarterly
    if quarterly:
        return 'partial',annual,quarterly
    return 'insufficient_data',annual,quarterly

def indexes(db):
    db.companies.create_index('ticker')
    # Unique financial indexes are built only after safe archival migration.
    db.largecap_collection_state.create_index('last_success_at')

def run(db,sec,limit,refresh_days,years,min_cap,force_refresh=False,tickers=None,universe_mode="sp500",universe_file=None):
    if limit<1 or refresh_days<0 or years<1 or min_cap<=0:raise ValueError('Invalid arguments')
    requested={normalize_ticker(t) for t in (tickers or []) if t.strip()}
    print(f'RUN_CONFIG limit={limit} refresh_days={refresh_days} force_refresh={force_refresh} years={years} tickers={sorted(requested)}',flush=True)
    official = sec_map(sec)
    universe=select_universe(universe_mode, official, tickers=tickers, csv_path=universe_file, min_cap=min_cap)
    # Resolve issuer identity BEFORE joining the S&P 500 universe. A ticker
    # feed match is not always the reporting issuer (notably XOM).
    resolved = {}
    conflicts = []
    for ticker, match in official.items():
        issuer, conflict = resolve_issuer(ticker, match)
        if conflict and issuer is None:
            conflicts.append((ticker, conflict))
        if issuer:
            resolved[ticker] = issuer
            if conflict:
                print(f'CIK_OVERRIDE ticker={ticker} SEC={match["cik"]} resolved={issuer["cik"]}', flush=True)
    companies=join_sec(universe,[{'ticker': t, 'cik_str': v['cik'], 'title': v['sec_name']} for t,v in resolved.items()])
    # Historical exclusions apply only to the S&P 500 membership workflow.
    if universe_mode == 'sp500':
        companies=[c for c in companies if c['ticker'] not in {'ACU','ADX','AEMRF','AIR','AKZOY','BKTI'}]
    if requested:
        matched=[c for c in companies if c['ticker'].upper() in requested]
        missing=requested-{c['ticker'].upper() for c in matched}
        if missing:raise ValueError(f'Unknown or unmapped requested tickers: {sorted(missing)}')
        companies=matched
    selected_conflicts=[(ticker, reason) for ticker, reason in conflicts
                        if ticker in {c['ticker'] for c in companies}]
    if selected_conflicts:
        raise RuntimeError(f'Unresolved SEC issuer identity mismatch: {selected_conflicts}')
    # Check stored CIKs against official map. Do not silently fetch another entity.
    for c in companies:
        stored=db.companies.find_one({'ticker': c['ticker']}, {'cik':1,'universe_class':1})
        if stored and stored.get('universe_class') == 'untracked_legacy_or_orphan':
            raise RuntimeError(f'Ticker marked untracked: {c["ticker"]}')
        if stored and stored.get('cik'):
            if cik10(stored['cik']) != cik10(c['cik']):
                raise RuntimeError(f'CIK sync required for {c["ticker"]}: DB={stored["cik"]} SEC={c["cik"]}')
    if not companies:raise RuntimeError('No SEC-mapped companies; aborting')
    print('MIGRATION_SUMMARY', migrate_all(db), flush=True)
    indexes(db)
    run_id=str(uuid4()); counts={'eligible':len(companies),'examined':0,'success':0,'partial':0,'insufficient_data':0,'skipped':0,'failed':0,'universe_source':universe[0]['universe_source'],'universe_mode':universe_mode}
    db.pipeline_runs.insert_one({'_id':run_id,'started_at':now(),'status':'running','version':'4.1.8.4','force_refresh':force_refresh})
    try:
        for company in companies[:limit]:
            counts['examined']+=1
            cik=company['cik']; state=db.largecap_collection_state.find_one({'_id':cik})
            if not due(state,refresh_days,force_refresh=force_refresh):counts['skipped']+=1;continue
            try:
                payload=sec.company_facts(cik)
                if int(payload.get('cik',-1))!=cik or not isinstance(payload.get('facts'),dict):raise ValueError('Invalid SEC payload')
                if requested:
                    print(f"SEC_INVENTORY {company['ticker']} mapped_cik={cik} mapped_name={company.get('name', company.get('title', ''))!r} {inventory(payload)}", flush=True)
                rows=normalize(payload,years=years)
                # Never write two operations for the same database identity.
                keys=[(r['period_type'],r['period_end']) for r in rows]
                if len(keys)!=len(set(keys)):
                    raise ValueError('Normalizer produced duplicate financial period identities')
                coverage, annual_count, quarterly_count = classify_periods(rows)
                if coverage != 'success':
                    print(f"DIAGNOSTIC {company['ticker']} {diagnose_annual(payload,years=years)}",flush=True)
                if coverage == 'insufficient_data':
                    # Never write or prune financial records on an empty response.
                    db.largecap_collection_state.update_one({'_id':cik},{'$set':{
                        'reporting_status':coverage,'annual_period_count':0,
                        'quarterly_period_count':0,'last_checked_at':now(),
                        'last_error':None,'failures':0,
                        'next_retry_at':now()+timedelta(days=max(refresh_days,1))}},upsert=True)
                    counts['insufficient_data']+=1
                    print(f"INSUFFICIENT_DATA {company['ticker']} CIK={cik} preserved_existing_data=True",flush=True)
                    continue
                for kind,coll in (('annual',db.financial_annual),('quarterly',db.financial_quarterly)):
                    selected=[r for r in rows if r['period_type']==kind]
                    if selected:
                        # v4.3.0: merge validated historical fields absent from the latest
                        # SEC normalization so scheduled refreshes cannot erase backfills.
                        # Fresh SEC values still take precedence; conflicts require audit.
                        operations=[]
                        for r in selected:
                            previous=coll.find_one({'cik':cik,'period_end':r['period_end']})
                            if previous:
                                for metric,value in (previous.get('metrics') or {}).items():
                                    if metric not in r['metrics'] and value is not None:
                                        r['metrics'][metric]=value
                                        if metric in (previous.get('metric_sources') or {}):
                                            r['metric_sources'][metric]=previous['metric_sources'][metric]
                            operations.append(ReplaceOne({'cik':cik,'period_end':r['period_end']},
                                {'cik':cik,'ticker':company['ticker'],**r,'updated_at':now()},upsert=True))
                        coll.bulk_write(operations,ordered=True)
                    # Remove older rows only after successful extraction and writes.
                    current_periods=[r['period_end'] for r in selected]
                    # Do not delete old records on a partial SEC response.
                    # Retention pruning is handled only after separate validation.
                # Safely quarantine legacy quarterly snapshots wrongly labeled Q1-Q3
                # at a verified annual fiscal year-end. Never delete legitimate Q4.
                annual_ends={r['period_end'] for r in rows if r['period_type']=='annual'}
                for old in db.financial_quarterly.find({'cik':cik,'period_end':{'$in':list(annual_ends)}}):
                    if old.get('fiscal_period') not in ('Q1','Q2','Q3'):continue
                    archive=dict(old)
                    archive['_id']=f"fiscal418:{cik}:{old['_id']}"
                    archive['archived_at']=now()
                    archive['archive_reason']='quarterly_label_at_verified_annual_year_end'
                    db.financial_period_archive.replace_one({'_id':archive['_id']},archive,upsert=True)
                    db.financial_quarterly.delete_one({'_id':old['_id'],'cik':cik})
                # Update the existing profile by ticker where present; don't
                # create a second profile with _id=CIK for the same ticker.
                profile=db.companies.find_one({'ticker':company['ticker']}, {'_id':1})
                profile_filter={'_id':profile['_id']} if profile else {'_id':cik}
                db.companies.update_one(profile_filter,{'$set':{k:v for k,v in company.items() if k!='cik'}|{'cik':f'{cik:010d}','universe_class':'tracked_collector','collector_universe':universe_mode,'updated_at':now()}},upsert=True)
                db.largecap_collection_state.update_one({'_id':cik},{'$set':{
                    'last_success_at':now(),'last_checked_at':now(),
                    'reporting_status':coverage,'annual_period_count':annual_count,
                    'quarterly_period_count':quarterly_count,
                    'failures':0,'next_retry_at':None,'last_error':None}},upsert=True)
                counts[coverage]+=1
                label='OK' if coverage=='success' else 'PARTIAL'
                print(f"{label} {company['ticker']} CIK={cik} annual={annual_count} quarterly={quarterly_count} periods={len(rows)}",flush=True)
            except Exception as exc:
                failures=int((state or {}).get('failures',0))+1
                db.largecap_collection_state.update_one({'_id':cik},{'$set':{'failures':failures,'next_retry_at':now()+timedelta(hours=min(2**min(failures,6),48)),'last_error':f'{type(exc).__name__}: {exc}'[:400]}},upsert=True)
                counts['failed']+=1
                print(f"FAILED {company['ticker']}: {type(exc).__name__}: {exc}",flush=True)
        status='completed' if not counts['failed'] else 'completed_with_errors'
    except Exception as exc:
        db.pipeline_runs.update_one({'_id':run_id},{'$set':{'status':'failed','finished_at':now(),'error':str(exc)[:400],'counts':counts}})
        raise
    db.pipeline_runs.update_one({'_id':run_id},{'$set':{'status':status,'finished_at':now(),'counts':counts}})
    return counts

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--limit',type=int,default=10)
    p.add_argument('--universe',choices=['sp500','us_large_cap','blackrock_holdings','sec_all','custom','tickers'],default='sp500')
    p.add_argument('--universe-file',default=None,help='CSV path with ticker header for --universe custom')
    p.add_argument('--tickers',default='',help='Comma-separated exact tickers within selected universe; only these are examined')
    p.add_argument('--force-refresh',action='store_true',help='Bypass both successful-refresh and failure-retry cooldowns')
    p.add_argument('--refresh-days',type=int,default=7)
    p.add_argument('--years',type=int,default=5)
    p.add_argument('--min-market-cap',type=float,default=10_000_000_000)
    args=p.parse_args()
    if args.universe=='tickers' and not args.tickers.strip():p.error('--universe tickers requires --tickers')
    if args.universe in ('custom', 'us_large_cap', 'blackrock_holdings') and not args.universe_file:p.error('--universe custom requires --universe-file')
    uri=os.environ.get('MONGODB_URI')
    if not uri:p.error('MONGODB_URI missing')
    sec=SecClient(os.environ.get('SEC_USER_AGENT'))
    with MongoClient(uri,tz_aware=True,serverSelectionTimeoutMS=15000) as client:
        client.admin.command('ping')
        result=run(client[os.environ.get('MONGODB_DATABASE','maketdata')],sec,args.limit,args.refresh_days,args.years,args.min_market_cap,force_refresh=args.force_refresh,tickers=args.tickers.split(',') if args.tickers.strip() else None,universe_mode=args.universe,universe_file=args.universe_file)
        print('COLLECTION_SUMMARY',result,flush=True)
        if result['failed']:raise SystemExit(1)
if __name__=='__main__':main()
