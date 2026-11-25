"""v4.3.2 guarded universe migration. Dry-run default, --apply explicit.

Deletes ONLY specified ticker company profiles. Financial records and state
are retained for separate review; deleting those can destroy history.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pymongo import MongoClient

ORPHANS=['ACU','ADX','AEMRF','AIR','AKZOY','BKTI']
SPINOFFS=['HONA','VYLR','FDXF','Q','SKYD','FERG','GEHC','SOLV','SW']

def cleanup(db,apply=False):
    planned={'orphan_profiles':list(db.companies.find({'ticker':{'$in':ORPHANS}})),
             'xom':list(db.companies.find({'ticker':'XOM'})),
             'spinoffs':list(db.companies.find({'ticker':{'$in':SPINOFFS}}))}
    report={'mode':'apply' if apply else 'dry_run','orphan_profiles':len(planned['orphan_profiles']),
            'xom_profiles':len(planned['xom']),'spinoff_profiles':len(planned['spinoffs']),
            'orphan_financial_records_preserved':True}
    if apply:
        # Save original profiles to an audit collection BEFORE any destructive action.
        stamp=datetime.now(timezone.utc).isoformat()
        for kind,docs in planned.items():
            for doc in docs:
                db.company_cleanup_archive.insert_one({'migration':'v4.3.2','run_at':stamp,'kind':kind,'original':doc})
        db.companies.delete_many({'ticker':{'$in':ORPHANS}})
        db.companies.update_many({'ticker':'XOM'},{'$set':{'cik':'0000034088'},'$unset':{'reporting_status':''}})
        db.companies.update_many({'ticker':{'$in':SPINOFFS}},{'$set':{'is_spinoff':True}})
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--apply',action='store_true')
    p.add_argument('--reingest',action='store_true',help='Recollect verified currently mapped tickers after --apply')
    args=p.parse_args()
    if not os.getenv('MONGODB_URI'):p.error('MONGODB_URI missing')
    with MongoClient(os.environ['MONGODB_URI']) as client:
        db=client[os.getenv('MONGODB_DATABASE','maketdata')]
        print(json.dumps(cleanup(db,args.apply)))
        if args.reingest:
            if not args.apply:p.error('--reingest requires --apply')
            from .collect import run
            from .sec_client import SecClient
            from .universe import fetch_large_caps, join_sec
            sec=SecClient(os.getenv('SEC_USER_AGENT'))
            eligible={c['ticker'] for c in join_sec(fetch_large_caps(),sec.tickers())}
            targets=[t for t in ['XOM',*SPINOFFS] if t in eligible]
            skipped=[t for t in ['XOM',*SPINOFFS] if t not in eligible]
            print(json.dumps({'reingest_tickers':targets,'unmapped_skipped':skipped}),flush=True)
            if targets:
                result=run(db,sec,len(targets),7,5,10_000_000_000,force_refresh=True,tickers=targets)
                print(json.dumps({'reingest_result':result},default=str),flush=True)
if __name__=='__main__':main()
