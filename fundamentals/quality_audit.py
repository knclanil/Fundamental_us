"""MaketData v4.2.0 read-only MongoDB financial coverage audit.

No mutation operations. Period counts describe stored data, not guaranteed SEC completeness.
"""
import argparse
import csv
import json
import os
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

from pymongo import MongoClient
from .balance_sheet import assess, reconciliation_diagnostics

METRICS = ('revenue','net_income','eps_basic','eps_diluted','assets','liabilities','equity',
           'operating_cash_flow','capex','free_cash_flow')
TOLERANCE = 0.02
VERSION = '4.3.2.5'

def iso(value):
    if isinstance(value, (datetime,date)):
        return value.isoformat()
    return str(value) if value is not None else None

def identity(row):
    """Canonical SEC CIK; numeric CIKs and zero-padded strings are identical."""
    value = row.get('cik')
    if value is None or str(value).strip() == '':
        value = row.get('_id')
    value = str(value).strip()
    if value.isdecimal() and len(value) <= 10:
        return value.zfill(10)
    return 'invalid:' + value

def fiscal_issues(rows):
    issues=[]
    seen=set()
    for row in rows:
        end=iso(row.get('period_end'))
        key=(identity(row),end)
        if key in seen:
            issues.append({'code':'duplicate_cik_period_end','period_end':end})
        seen.add(key)
        if not end:
            issues.append({'code':'missing_period_end'})
        period=row.get('fiscal_period')
        kind=row.get('period_type')
        if kind == 'annual' and period in ('Q1','Q2','Q3'):
            issues.append({'code':'annual_quarter_label','period_end':end,'label':period})
        if kind == 'quarterly' and period == 'FY':
            issues.append({'code':'quarterly_fy_label','period_end':end})
    return issues

def cashflow_issues(rows):
    issues=[]
    for row in rows:
        sources=row.get('metric_sources') or {}
        for metric in ('operating_cash_flow','capex'):
            source=sources.get(metric) or {}
            if source.get('method') != 'ytd_difference':
                continue
            current=source.get('current') or {}
            previous=source.get('previous') or {}
            if current.get('start') and previous.get('start') and iso(current['start']) != iso(previous['start']):
                issues.append({'code':'ytd_start_mismatch','metric':metric,'period_end':iso(row.get('period_end'))})
            if not current.get('start') or not previous.get('start') or not current.get('end') or not previous.get('end'):
                issues.append({'code':'ytd_missing_source_dates','metric':metric,'period_end':iso(row.get('period_end'))})
            if current.get('end') and previous.get('end') and iso(current['end']) <= iso(previous['end']):
                issues.append({'code':'ytd_end_order','metric':metric,'period_end':iso(row.get('period_end'))})
    return issues

def reconcile(rows):
    issues=[]
    for row in rows:
        check=assess(row.get('metrics') or {})
        if check['status'] in ('unreconciled','scale_outlier'):
            issues.append({'code':'balance_sheet_unreconciled' if check['status']=='unreconciled' else 'balance_sheet_scale_outlier',
                           'period_end':iso(row.get('period_end')),
                           'residual':check['residual'],
                           'relative_to_assets':round(check['relative_difference'],6),
                           'note':'Review SEC provenance; do not auto-overwrite reported facts',
                           'diagnostics':reconciliation_diagnostics(row.get('metrics') or {}, row.get('metric_sources') or {})})
    return issues

def analyze_company(company,annual,quarterly,state=None):
    all_rows=annual+quarterly
    missing={metric:sum((r.get('metrics') or {}).get(metric) is None for r in all_rows) for metric in METRICS}
    issues=[]
    for kind,rows in (('annual',annual),('quarterly',quarterly)):
        for issue in fiscal_issues(rows):issues.append({'collection':kind,**issue})
        for issue in reconcile(rows):issues.append({'collection':kind,**issue})
        for issue in cashflow_issues(rows):issues.append({'collection':kind,**issue})
    status=(state or {}).get('reporting_status') or company.get('reporting_status')
    spinoff=bool(company.get('is_spinoff'))
    info=[]
    if len(annual)<5:
        finding={'code':'annual_coverage_below_target','found':len(annual),'target':5}
        (info if spinoff or status=='partial' else issues).append(finding)
    if len(quarterly)<16:
        finding={'code':'quarterly_history_short_review','found':len(quarterly),'reference':20}
        (info if spinoff or status=='partial' else issues).append(finding)
    latest=max((iso(r.get('period_end')) for r in all_rows if r.get('period_end')),default=None)
    return {'cik':identity(company),'ticker':company.get('ticker'),'name':company.get('name') or company.get('title'),
            'reporting_status':status,'is_spinoff':spinoff,'informational_notes':info,'universe_class':'tracked_collector' if state else 'untracked_legacy_or_orphan','annual_count':len(annual),
            'quarterly_count':len(quarterly),'latest_period_end':latest,
            'missing_metric_counts':missing,'issue_count':len(issues),'issues':issues}

def generate(db,expected=500):
    companies=list(db.companies.find({}, {'_id':1,'cik':1,'ticker':1,'name':1,'title':1,'is_spinoff':1,'reporting_status':1,'universe_class':1}))
    annual=defaultdict(list);quarterly=defaultdict(list)
    for row in db.financial_annual.find({}, {'_id':0}):annual[identity(row)].append(row)
    for row in db.financial_quarterly.find({}, {'_id':0}):quarterly[identity(row)].append(row)
    states=defaultdict(list)
    for state in db.largecap_collection_state.find({}, {'_id':1,'cik':1,'reporting_status':1}):
        states[identity(state)].append(state)
    profiles=defaultdict(list)
    for company in companies:
        profiles[identity(company)].append(company)
    keys=set(profiles)|set(annual)|set(quarterly)|set(states)
    results=[]; collisions=[]; unmatched=[]
    for cik in sorted(keys):
        candidates=profiles.get(cik,[])
        if len(candidates)>1:
            collisions.append({'cik':cik,'profile_ids':[str(c['_id']) for c in candidates],
                               'tickers':[c.get('ticker') for c in candidates]})
        # Never silently merge conflicting ticker profiles. Report the conflict.
        company=next((c for c in candidates if c.get('ticker') and c.get('universe_class')!='untracked_legacy_or_orphan'),
                     next((c for c in candidates if c.get('ticker')), candidates[0] if candidates else {'_id':cik}))
        state=states[cik][0] if states.get(cik) else None
        result=analyze_company(company,annual.get(cik,[]),quarterly.get(cik,[]),state)
        result['cik']=cik
        result['universe_class']='tracked_collector' if state else ('profile_without_collector_state' if candidates else 'financial_without_profile')
        result['profile_count']=len(candidates)
        result['identity_conflict']=len(candidates)>1
        if not candidates or not state:
            unmatched.append({'cik':cik,'ticker':company.get('ticker'),'reason':
                              'no_company_profile' if not candidates else 'no_collector_state'})
        results.append(result)
    results.sort(key=lambda r:(r.get('ticker') or '',r['cik']))
    issue_counts=Counter(i['code'] for r in results for i in r['issues'])
    summary={'generated_at':datetime.now(timezone.utc).isoformat(),'expected_companies':expected,
             'companies_in_database_or_state':len(results),'unique_normalized_ciks':len(results),
             'company_profile_documents':len(companies),'identity_collision_count':len(collisions),
             'unmatched_identity_count':len(unmatched),
             'tracked_collector_companies':sum(r['universe_class']=='tracked_collector' for r in results),
             'untracked_legacy_or_orphan_companies':sum(r['universe_class']!='tracked_collector' for r in results),
             'companies_with_annual':sum(bool(r['annual_count']) for r in results),
             'companies_with_quarterly':sum(bool(r['quarterly_count']) for r in results),
             'annual_documents':sum(r['annual_count'] for r in results),
             'quarterly_documents':sum(r['quarterly_count'] for r in results),
             'companies_with_5_annual':sum(r['annual_count']>=5 for r in results),
             'companies_with_20_quarterly':sum(r['quarterly_count']>=20 for r in results),
             'issue_counts':dict(sorted(issue_counts.items())),
             'informational_notes':sum(len(r['informational_notes']) for r in results),
             'quarterly_19_or_more':sum(r['quarterly_count']>=19 for r in results),
             'note_on_quarters':'A 19-quarter history can be valid. Under 16 triggers review.',
             'note':'Read-only audit; identity collisions and balance-sheet differences require source review.'}
    return {'version':VERSION,'summary':summary,'companies':results,
            'identity_collisions':collisions,'unmatched_identities':unmatched}

def write_reports(report,output):
    path=Path(output);path.mkdir(parents=True,exist_ok=True)
    (path/'quality_report.json').write_text(json.dumps(report,indent=2,default=iso)+'\n',encoding='utf-8')
    with (path/'identity_review.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.writer(handle);writer.writerow(['cik','issue','details'])
        for c in report.get('identity_collisions',[]):writer.writerow([c['cik'],'multiple_profiles',json.dumps(c,sort_keys=True)])
        for c in report.get('unmatched_identities',[]):writer.writerow([c['cik'],c['reason'],json.dumps(c,sort_keys=True)])
    with (path/'company_coverage.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.writer(handle)
        writer.writerow(['ticker','cik','name','reporting_status','universe_class','annual_count','quarterly_count','latest_period_end','issue_count',*[f'missing_{m}' for m in METRICS]])
        for r in report['companies']:
            writer.writerow([r['ticker'],r['cik'],r['name'],r['reporting_status'],r['universe_class'],r['annual_count'],r['quarterly_count'],r['latest_period_end'],r['issue_count'],*[r['missing_metric_counts'][m] for m in METRICS]])
    with (path/'quality_issues.csv').open('w',newline='',encoding='utf-8') as handle:
        writer=csv.writer(handle);writer.writerow(['ticker','cik','collection','code','period_end','details'])
        for r in report['companies']:
            for issue in r['issues']:
                writer.writerow([r['ticker'],r['cik'],issue.get('collection'),issue['code'],issue.get('period_end'),json.dumps(issue,default=iso,sort_keys=True)])

def main():
    parser=argparse.ArgumentParser(description='Read-only MongoDB financial data quality report')
    parser.add_argument('--output',default='artifacts/financial-quality')
    parser.add_argument('--expected',type=int,default=500)
    args=parser.parse_args()
    uri=os.getenv('MONGODB_URI')
    if not uri:parser.error('MONGODB_URI missing')
    with MongoClient(uri,tz_aware=True,serverSelectionTimeoutMS=15000) as client:
        client.admin.command('ping')
        report=generate(client[os.getenv('MONGODB_DATABASE','maketdata')],args.expected)
    write_reports(report,args.output)
    print('QUALITY_AUDIT_SUMMARY',json.dumps(report['summary'],sort_keys=True),flush=True)
    print('QUALITY_AUDIT_OUTPUT',args.output,flush=True)
if __name__=='__main__':main()
