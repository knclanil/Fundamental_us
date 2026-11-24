"""Large-cap, five-year, incremental SEC fundamentals collector."""
import argparse
import os
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from pymongo import MongoClient,UpdateOne,ReplaceOne,ASCENDING
from .sec_client import SecClient
from .universe import fetch_large_caps,join_sec
from .normalize import normalize
from .migrate import migrate_all

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

def indexes(db):
    db.companies.create_index('ticker')
    # Unique financial indexes are built only after safe archival migration.
    db.largecap_collection_state.create_index('last_success_at')

def run(db,sec,limit,refresh_days,years,min_cap,force_refresh=False):
    if limit<1 or refresh_days<0 or years<1 or min_cap<=0:raise ValueError('Invalid arguments')
    print(f'RUN_CONFIG limit={limit} refresh_days={refresh_days} force_refresh={force_refresh} years={years}',flush=True)
    universe=fetch_large_caps(min_cap)
    companies=join_sec(universe,sec.tickers())
    if not companies:raise RuntimeError('No SEC-mapped large caps; aborting')
    print('MIGRATION_SUMMARY', migrate_all(db), flush=True)
    indexes(db)
    run_id=str(uuid4()); counts={'eligible':len(companies),'examined':0,'success':0,'skipped':0,'failed':0,'universe_source':universe[0]['universe_source']}
    db.pipeline_runs.insert_one({'_id':run_id,'started_at':now(),'status':'running','version':'4.1.7','force_refresh':force_refresh})
    try:
        for company in companies[:limit]:
            counts['examined']+=1
            cik=company['cik']; state=db.largecap_collection_state.find_one({'_id':cik})
            if not due(state,refresh_days,force_refresh=force_refresh):counts['skipped']+=1;continue
            try:
                payload=sec.company_facts(cik)
                if int(payload.get('cik',-1))!=cik or not isinstance(payload.get('facts'),dict):raise ValueError('Invalid SEC payload')
                rows=normalize(payload,years=years)
                # Never write two operations for the same database identity.
                keys=[(r['period_type'],r['period_end']) for r in rows]
                if len(keys)!=len(set(keys)):
                    raise ValueError('Normalizer produced duplicate financial period identities')
                if not rows:raise ValueError('No normalized SEC financial periods; preserving previous data')
                if not any(r['period_type']=='annual' for r in rows):raise ValueError('No annual financial periods; preserving previous data')
                for kind,coll in (('annual',db.financial_annual),('quarterly',db.financial_quarterly)):
                    selected=[r for r in rows if r['period_type']==kind]
                    if selected:
                        coll.bulk_write([ReplaceOne({'cik':cik,'period_end':r['period_end']},{'cik':cik,'ticker':company['ticker'],**r,'updated_at':now()},upsert=True) for r in selected], ordered=True)
                    # Remove older rows only after successful extraction and writes.
                    current_periods=[r['period_end'] for r in selected]
                    # Do not delete old records on a partial SEC response.
                    # Retention pruning is handled only after separate validation.
                db.companies.update_one({'_id':cik},{'$set':{k:v for k,v in company.items() if k!='cik'}|{'updated_at':now()}},upsert=True)
                db.largecap_collection_state.update_one({'_id':cik},{'$set':{'last_success_at':now(),'failures':0,'next_retry_at':None,'last_error':None}},upsert=True)
                counts['success']+=1
                print(f"OK {company['ticker']} CIK={cik} periods={len(rows)}",flush=True)
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
    p.add_argument('--force-refresh',action='store_true',help='Bypass both successful-refresh and failure-retry cooldowns')
    p.add_argument('--refresh-days',type=int,default=7)
    p.add_argument('--years',type=int,default=5)
    p.add_argument('--min-market-cap',type=float,default=10_000_000_000)
    args=p.parse_args()
    uri=os.environ.get('MONGODB_URI')
    if not uri:p.error('MONGODB_URI missing')
    sec=SecClient(os.environ.get('SEC_USER_AGENT'))
    with MongoClient(uri,tz_aware=True,serverSelectionTimeoutMS=15000) as client:
        client.admin.command('ping')
        result=run(client[os.environ.get('MONGODB_DATABASE','maketdata')],sec,args.limit,args.refresh_days,args.years,args.min_market_cap,force_refresh=args.force_refresh)
        print('COLLECTION_SUMMARY',result,flush=True)
        if result['failed']:raise SystemExit(1)
if __name__=='__main__':main()
