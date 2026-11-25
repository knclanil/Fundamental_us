"""v4.2.2 read-mostly Q4 backfill. Default dry-run; writes only absent metrics."""
import argparse
import os
from datetime import datetime, timezone
from .q4_completion import complete_q4


def plan_company(annual_docs, quarter_docs):
    """Produce conservative updates without modifying any input documents."""
    planned=[]
    for annual in annual_docs:
        fy=annual.get('fiscal_year'); end=annual.get('period_end')
        matches=[q for q in quarter_docs if q.get('fiscal_year')==fy and
                 q.get('fiscal_period')=='Q4' and q.get('period_end')==end]
        if len(matches)!=1:continue
        q4=matches[0]
        candidates, sources=complete_q4(annual,quarter_docs)
        additions={k:v for k,v in candidates.items() if k not in (q4.get('metrics') or {})}
        if additions:planned.append((q4,additions,{k:sources[k] for k in additions}))
    return planned


def main():
    p=argparse.ArgumentParser(description='Q4 completion: default dry-run, --apply for guarded writes')
    p.add_argument('--tickers',default='AAPL',help='Comma-separated tickers, or ALL')
    p.add_argument('--apply',action='store_true',help='Write only missing fields (no deletes/replacements)')
    p.add_argument('--max-companies',type=int,default=500)
    args=p.parse_args()
    if args.max_companies<1:p.error('--max-companies must be positive')
    uri=os.environ.get('MONGODB_URI')
    if not uri:p.error('MONGODB_URI missing')
    from pymongo import MongoClient
    with MongoClient(uri,tz_aware=True,serverSelectionTimeoutMS=15000) as client:
        client.admin.command('ping')
        db=client[os.environ.get('MONGODB_DATABASE','maketdata')]
        if args.tickers.strip().upper()=='ALL':
            tickers=sorted(set(db.financial_annual.distinct('ticker')))[:args.max_companies]
        else:tickers=list(dict.fromkeys(t.strip().upper() for t in args.tickers.split(',') if t.strip()))[:args.max_companies]
        totals={'companies':0,'q4_records':0,'metrics_planned':0,'metrics_written':0,'conflicts':0}
        for ticker in tickers:
            annual=list(db.financial_annual.find({'ticker':ticker}))
            quarterly=list(db.financial_quarterly.find({'ticker':ticker}))
            plans=plan_company(annual,quarterly)
            totals['companies']+=1
            for q4,metrics,sources in plans:
                totals['q4_records']+=1;totals['metrics_planned']+=len(metrics)
                print(f"{'APPLY' if args.apply else 'DRY_RUN'} {ticker} {q4['period']} add={sorted(metrics)}",flush=True)
                if not args.apply:continue
                # Guard each metric independently against concurrent writes.
                # Never overwrite a preexisting metric or provenance field.
                for metric,value in metrics.items():
                    result=db.financial_quarterly.update_one(
                        {'_id':q4['_id'],f'metrics.{metric}':{'$exists':False},
                         f'metric_sources.{metric}':{'$exists':False}},
                        {'$set':{f'metrics.{metric}':value,
                                 f'metric_sources.{metric}':sources[metric],
                                 'updated_at':datetime.now(timezone.utc)}})
                    if result.modified_count:totals['metrics_written']+=1
                    else:totals['conflicts']+=1
        print('Q4_COMPLETION_SUMMARY',totals,flush=True)
        if totals['conflicts']:raise SystemExit(2)

if __name__=='__main__':main()
