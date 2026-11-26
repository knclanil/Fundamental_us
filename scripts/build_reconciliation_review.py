"""Create a deduplicated, read-only targeted review queue from a quality audit ZIP.
Usage: python scripts/build_reconciliation_review.py --audit audit.zip --output review.csv
No MongoDB writes or SEC requests.
"""
import argparse
import csv
import io
import json
import zipfile
from collections import defaultdict
from pathlib import Path

CODES = {'balance_sheet_unreconciled', 'balance_sheet_scale_outlier'}

def build(audit_zip, output):
    with zipfile.ZipFile(audit_zip) as archive:
        reader = csv.DictReader(io.TextIOWrapper(archive.open('quality_issues.csv'), encoding='utf-8-sig'))
        issues = [row for row in reader if row.get('code') in CODES]
    grouped = defaultdict(list)
    for issue in issues:
        key = (issue.get('cik','').zfill(10), issue.get('ticker',''))
        grouped[key].append(issue)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=['cik','ticker','affected_periods',
            'annual_periods','quarterly_periods','scale_outliers','max_relative_difference',
            'period_ends','review_status'])
        writer.writeheader()
        for (cik,ticker), rows in sorted(grouped.items()):
            details = []
            for row in rows:
                try: details.append(json.loads(row.get('details') or '{}'))
                except json.JSONDecodeError: details.append({})
            writer.writerow({'cik':cik,'ticker':ticker,'affected_periods':len(rows),
                'annual_periods':sum(r['collection']=='annual' for r in rows),
                'quarterly_periods':sum(r['collection']=='quarterly' for r in rows),
                'scale_outliers':sum(r['code']=='balance_sheet_scale_outlier' for r in rows),
                'max_relative_difference':max((float(d.get('relative_to_assets') or 0) for d in details),default=0),
                'period_ends':';'.join(sorted(set(r.get('period_end','') for r in rows))),
                'review_status':'PENDING_SOURCE_REVIEW'})
    return len(grouped), len(issues)

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--audit',required=True)
    parser.add_argument('--output',default='reconciliation_review.csv')
    args=parser.parse_args()
    companies,periods=build(args.audit,args.output)
    print(f'RECONCILIATION_REVIEW companies={companies} periods={periods} output={args.output}')
