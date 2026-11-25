"""v4.3.0 conservative SEC financial repair: dry-run by default.

No existing non-null metric is overwritten. Conflicts and unreconciled balance
sheets are reported for investigation, not automatically rewritten.
"""
import argparse
import csv
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from pymongo import MongoClient
from .normalize import normalize
from .sec_client import SecClient
from .quality_audit import reconcile

VERSION = '4.3.0'

def missing(value):
    return value is None

def identity(row):
    return (row.get('period_type'), row.get('period_end'))

def plan(existing, extracted):
    """Return safe additions and conflicts for one matching reporting period.

    The source normalizer must supply metric_sources for every SEC value.
    No synthetic records or overwrites are generated here.
    """
    old_metrics = existing.get('metrics') or {}
    old_sources = existing.get('metric_sources') or {}
    new_metrics = extracted.get('metrics') or {}
    new_sources = extracted.get('metric_sources') or {}
    additions, conflicts, skipped = {}, [], []
    for metric, value in new_metrics.items():
        source = new_sources.get(metric)
        if missing(value) or not source:
            skipped.append(metric)
            continue
        if not missing(old_metrics.get(metric)):
            if old_metrics[metric] != value:
                conflicts.append({'metric':metric,'stored':old_metrics[metric], 'sec_candidate':value,
                                  'source':source})
            continue
        if metric in old_sources and old_sources[metric]:
            skipped.append(metric)  # provenance conflict: don't overwrite
            continue
        additions[metric] = {'value':value,'source':source}
    return additions, conflicts, skipped

def safe_update(collection, row, metric, value, source):
    """Atomic conditional update, guarded against concurrent writes.

    A stored explicit null is eligible; an existing non-null value is not.
    """
    selector = {'_id':row['_id'], '$and':[
        {'$or':[{f'metrics.{metric}':{'$exists':False}}, {f'metrics.{metric}':None}]},
        {f'metric_sources.{metric}':{'$exists':False}}
    ]}
    return collection.update_one(selector, {'$set':{
        f'metrics.{metric}':value,
        f'metric_sources.{metric}':source,
        'updated_at':datetime.now(timezone.utc)
    }}).modified_count

def check_candidate_balance(existing, additions):
    """Do not insert a candidate if it would create a new material imbalance.

    If the existing record is already inconsistent, do not automatically block
    unrelated metrics; report the imbalance separately.
    """
    before = existing.get('metrics') or {}
    after = dict(before)
    after.update({k:v['value'] for k,v in additions.items()})
    trio = ('assets','liabilities','equity')
    if not any(k in additions for k in trio):return True
    if not all(isinstance(after.get(k),(int,float)) and not isinstance(after.get(k),bool) for k in trio):
        return True  # cannot assess yet
    issues_after = reconcile([{'period_end':existing.get('period_end'),'metrics':after}])
    if not issues_after:return True
    if all(isinstance(before.get(k),(int,float)) for k in trio):
        issues_before = reconcile([{'period_end':existing.get('period_end'),'metrics':before}])
        if issues_before and abs(issues_after[0]['residual']) < abs(issues_before[0]['residual']):
            return True
    return False

def repair_company(db, sec, company, years=5, apply=False):
    ticker=company['ticker']; cik=int(company['_id'])
    payload=sec.company_facts(cik)
    if int(payload.get('cik',-1)) != cik:raise ValueError('SEC CIK mismatch')
    extracted=normalize(payload,years=years)
    candidates={identity(r):r for r in extracted}
    if len(candidates)!=len(extracted):raise ValueError('Duplicate normalized period identity')
    records=[]; totals=Counter()
    for kind,coll in (('annual',db.financial_annual),('quarterly',db.financial_quarterly)):
        for old in coll.find({'cik':cik}):
            key=identity(old); candidate=candidates.get(key)
            if not candidate:
                totals['periods_not_in_sec_normalization']+=1
                continue
            additions,conflicts,skipped=plan(old,candidate)
            totals['conflicts']+=len(conflicts)
            for conflict in conflicts:
                records.append({'ticker':ticker,'cik':cik,'collection':kind,'period':old.get('period'),
                    'period_end':old.get('period_end'),'metric':conflict['metric'],'status':'CONFLICT',
                    'stored':conflict['stored'],'candidate':conflict['sec_candidate'],
                    'source':conflict['source']})
            for metric,item in additions.items():
                if metric in ('assets','liabilities','equity') and not check_candidate_balance(old,{metric:item}):
                    totals['balance_guard_rejections']+=1
                    records.append({'ticker':ticker,'cik':cik,'collection':kind,'period':old.get('period'),
                        'period_end':old.get('period_end'),'metric':metric,'status':'BALANCE_REVIEW',
                        'candidate':item['value'],'source':item['source']})
                    continue
                status='PLANNED'
                if apply:
                    status='WRITTEN' if safe_update(coll,old,metric,item['value'],item['source']) else 'WRITE_CONFLICT'
                totals[status.lower()]+=1
                records.append({'ticker':ticker,'cik':cik,'collection':kind,'period':old.get('period'),
                    'period_end':old.get('period_end'),'metric':metric,'status':status,
                    'candidate':item['value'],'source':item['source']})
            totals['existing_periods_matched']+=1
    # Explicitly report SEC-normalized periods missing in DB; do not create blindly.
    for key,row in candidates.items():
        coll=db.financial_annual if key[0]=='annual' else db.financial_quarterly
        if coll.count_documents({'cik':cik,'period_end':key[1]},limit=1)==0:
            totals['new_period_candidates']+=1
            records.append({'ticker':ticker,'cik':cik,'collection':key[0],
                'period':row.get('period'),'period_end':key[1], 'metric':'*',
                'status':'NEW_PERIOD_REVIEW','candidate':len(row.get('metrics') or {})})
    return records, totals

def run(db,sec,tickers,apply=False,years=5):
    results=[]; totals=Counter()
    for ticker in tickers:
        company=db.companies.find_one({'ticker':ticker})
        if not company:
            totals['unknown_companies']+=1
            results.append({'ticker':ticker,'status':'UNKNOWN_COMPANY'})
            continue
        try:
            rows,counts=repair_company(db,sec,company,years=years,apply=apply)
            results.extend(rows);totals.update(counts);totals['companies_processed']+=1
            print('COMPANY',ticker,dict(counts),flush=True)
        except Exception as exc:
            totals['companies_failed']+=1
            results.append({'ticker':ticker,'status':'ERROR','detail':f'{type(exc).__name__}: {exc}'[:300]})
            print('COMPANY_FAILED',ticker,type(exc).__name__,str(exc)[:200],flush=True)
    return results,dict(totals)

def save_report(rows,summary,path,apply):
    directory=Path(path);directory.mkdir(parents=True,exist_ok=True)
    report={'version':VERSION,'mode':'APPLY' if apply else 'DRY_RUN',
            'generated_at':datetime.now(timezone.utc).isoformat(),
            'summary':summary,'limitations':[
                'No existing non-null values corrected automatically',
                'New periods reported but not inserted automatically',
                'Industry-specific SEC custom XBRL extensions not parsed',
                'Unresolved balance-sheet mismatches require source review',
                'Report does not independently certify SEC financial accuracy']}
    (directory/'repair_summary.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    fields=['ticker','cik','collection','period','period_end','metric','status','stored','candidate','source','detail']
    with (directory/'repair_details.csv').open('w',newline='',encoding='utf-8') as fh:
        writer=csv.DictWriter(fh,fieldnames=fields,extrasaction='ignore');writer.writeheader()
        for row in rows:
            cleaned={**row,'source':json.dumps(row.get('source') or {},default=str)}
            writer.writerow(cleaned)

def main():
    parser=argparse.ArgumentParser(description='v4.3.0 guarded SEC repair; dry-run default')
    parser.add_argument('--tickers',default='AAPL',help='Comma-separated tickers or ALL')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--years',type=int,default=5)
    parser.add_argument('--max-companies',type=int,default=500)
    parser.add_argument('--output',default='artifacts/financial-repair')
    args=parser.parse_args()
    if args.years<1 or args.max_companies<1:parser.error('Invalid years/max-companies')
    uri=os.getenv('MONGODB_URI')
    if not uri:parser.error('MONGODB_URI missing')
    sec=SecClient(os.getenv('SEC_USER_AGENT'))
    with MongoClient(uri,tz_aware=True,serverSelectionTimeoutMS=15000) as client:
        client.admin.command('ping')
        db=client[os.getenv('MONGODB_DATABASE','maketdata')]
        if args.tickers.strip().upper()=='ALL':
            # Only companies in tracked collection state; exclude orphan legacy tickers.
            ciks=set(db.largecap_collection_state.distinct('_id'))
            tickers=sorted({c['ticker'] for c in db.companies.find({'_id':{'$in':list(ciks)}},{'ticker':1})
                            if c.get('ticker')})[:args.max_companies]
        else:
            tickers=list(dict.fromkeys(x.strip().upper() for x in args.tickers.split(',') if x.strip()))[:args.max_companies]
        rows,summary=run(db,sec,tickers,apply=args.apply,years=args.years)
    save_report(rows,summary,args.output,args.apply)
    print('FINANCIAL_REPAIR_SUMMARY',json.dumps(summary,sort_keys=True),flush=True)
    if summary.get('companies_failed') or summary.get('write_conflict'):raise SystemExit(2)

if __name__=='__main__':main()
