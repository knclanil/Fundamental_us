"""SEC ticker/CIK synchronization. v4.3.2.2 (2026-11-25).

Dry-run by default. SEC's ticker file is a mapping, not proof of current
S&P 500 membership, active filing status, or issuer continuity.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from .sec_client import SecClient

LEGACY = {'ACU', 'ADX', 'AEMRF', 'AIR', 'AKZOY', 'BKTI'}
# Identity guard: the SEC ticker list can occasionally map a familiar symbol
# to an unexpected entity. Do not silently reassign a known parent issuer.
EXPECTED_ISSUERS = {'XOM': ('0000034088', 'EXXON MOBIL')}

def normalize_ticker(ticker):
    return str(ticker or '').strip().upper().replace('.', '-')

def cik10(value):
    if value is None or str(value).strip() == '':
        return ''
    value = str(value).strip()
    if not value.isdigit() or len(value) > 10:
        raise ValueError('Invalid CIK: ' + value)
    return value.zfill(10)

def sec_map(sec):
    mapping = {}
    for row in sec.tickers():
        ticker = normalize_ticker(row['ticker'])
        if ticker in mapping and mapping[ticker]['cik'] != cik10(row['cik_str']):
            raise ValueError('Conflicting SEC ticker mapping: ' + ticker)
        mapping[ticker] = {'cik': cik10(row['cik_str']), 'sec_name': str(row['title']).strip()}
    return mapping

def issuer_guard(ticker, match):
    expected = EXPECTED_ISSUERS.get(ticker)
    if not expected:
        return None
    if match['cik'] != expected[0] or expected[1] not in match['sec_name'].upper():
        return f'identity_mismatch expected={expected[0]} SEC={match["cik"]} name={match["sec_name"]}'
    return None

def sync_and_clean_ciks(db, sec, apply=False):
    mapping = sec_map(sec)  # one SEC fetch, reused for entire run
    report = {'mode': 'apply' if apply else 'dry_run', 'sec_tickers': len(mapping),
              'scanned': 0, 'cik_changes': [], 'unchanged': 0,
              'untracked': [], 'identity_conflicts': [], 'errors': []}
    for doc in db.companies.find({}, {'_id': 1, 'ticker': 1, 'cik': 1, 'sec_name': 1, 'universe_class': 1}):
        report['scanned'] += 1
        ticker = normalize_ticker(doc.get('ticker'))
        if not ticker:
            report['errors'].append({'id': str(doc['_id']), 'reason': 'empty_ticker'})
            continue
        match = mapping.get(ticker)
        # Explicitly excluded historical tickers remain excluded even if an SEC
        # ticker file still contains them (SEC list != S&P 500 membership).
        if ticker in LEGACY or match is None:
            report['untracked'].append(ticker)
            if apply:
                db.companies.update_one({'_id': doc['_id']}, {'$set': {
                    'universe_class': 'untracked_legacy_or_orphan',
                    'cik_sync_at': datetime.now(timezone.utc)}})
            continue
        conflict = issuer_guard(ticker, match)
        if conflict:
            report['identity_conflicts'].append({'ticker': ticker, 'reason': conflict})
            # No write for identity conflict; do not replace XOM with subsidiary.
            continue
        try:
            old = cik10(doc.get('cik'))
        except ValueError:
            old = str(doc.get('cik'))
        if old != match['cik']:
            report['cik_changes'].append({'ticker': ticker, 'old': old, 'new': match['cik']})
        else:
            report['unchanged'] += 1
        if apply:
            # Archive original record before changing a CIK; preserve _id.
            if old != match['cik']:
                db.cik_sync_archive.insert_one({'ticker': ticker, 'at': datetime.now(timezone.utc),
                                                'original': doc, 'new_cik': match['cik']})
            db.companies.update_one({'_id': doc['_id']}, {'$set': {
                'cik': match['cik'], 'sec_name': match['sec_name'],
                'universe_class': 'tracked_collector',
                'cik_sync_at': datetime.now(timezone.utc)}})
    report['cik_changes_count'] = len(report['cik_changes'])
    report['untracked_count'] = len(report['untracked'])
    report['identity_conflicts_count'] = len(report['identity_conflicts'])
    return report

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true', help='Write CIK updates (default dry-run)')
    args = p.parse_args()
    if not os.getenv('MONGODB_URI'):
        p.error('MONGODB_URI missing')
    sec = SecClient(os.getenv('SEC_USER_AGENT'))
    from pymongo import MongoClient
    with MongoClient(os.environ['MONGODB_URI'], tz_aware=True) as client:
        client.admin.command('ping')
        report = sync_and_clean_ciks(client[os.getenv('MONGODB_DATABASE', 'maketdata')], sec, args.apply)
        print('CIK_SYNC_SUMMARY', json.dumps(report, default=str), flush=True)
        if report['identity_conflicts'] or report['errors']:
            raise SystemExit('CIK sync requires review: identity conflicts or invalid records')
if __name__ == '__main__':
    main()
