"""v4.3.2.14: automated ETF discovery, safe Mongo profile sync, resumable SEC batches.

ETF membership is NOT proof of >= $10B market capitalization. When a verified
market-cap CSV is supplied, eligibility is the intersection of both universes.
"""
import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from pymongo import MongoClient
from .blackrock_holdings import read_combined
from .cik_sync import sec_map, resolve_issuer, cik10
from .sec_client import SecClient
from .universe import load_us_large_cap
from .collect import run


def build_universe(holdings_path, official, market_cap_csv=None):
    holdings = read_combined(holdings_path)
    eligible = None
    if market_cap_csv:
        eligible = {r['ticker']: r for r in load_us_large_cap(market_cap_csv, official)}
    out, unmatched, conflicts = [], [], []
    seen = set()
    for h in holdings:
        ticker = h['ticker'].strip().upper().replace('.', '-')
        if eligible is not None and ticker not in eligible:
            continue
        mapped = official.get(ticker)
        if not mapped:
            unmatched.append(ticker)
            continue
        issuer, conflict = resolve_issuer(ticker, mapped)
        if not issuer:
            conflicts.append({'ticker': ticker, 'reason': conflict or 'unresolved issuer'})
            continue
        cik = int(issuer['cik'])
        if cik in seen:
            continue
        seen.add(cik)
        profile = {'ticker': ticker, 'cik': cik10(cik),
                   'name': issuer['sec_name'], 'universe_source': 'blackrock_etf_holdings',
                   'holdings_as_of': h['holdings_as_of'],
                   'in_IWB': int(h['in_IWB']), 'in_IWM': int(h['in_IWM']),
                   'in_IWV': int(h['in_IWV']), 'sector': h['sector'],
                   'exchange': h['exchange'], 'location': h['location']}
        if eligible is not None:
            profile.update({k: eligible[ticker][k] for k in ('market_cap_usd','market_cap_as_of','market_cap_source')})
            profile['universe_source'] = 'blackrock_etf_and_verified_market_cap'
        out.append(profile)
    out.sort(key=lambda p: (p['cik'], p['ticker']))
    if not out:
        raise ValueError('No SEC-matched eligible issuers; refusing empty universe sync')
    return out, unmatched, conflicts


def sync_profiles(db, profiles, snapshot_id, allow_changes=True):
    """Non-destructive profile sync; refuse CIK/ticker conflicts rather than overwrite."""
    now = datetime.now(timezone.utc)
    inserted = updated = blocked = 0
    for p in profiles:
        ticker, cik = p['ticker'], p['cik']
        existing = db.companies.find_one({'ticker': ticker}, {'_id': 1, 'cik': 1, 'universe_class': 1})
        if existing and existing.get('cik') and cik10(existing['cik']) != cik:
            blocked += 1
            continue
        if existing and existing.get('universe_class') == 'untracked_legacy_or_orphan':
            blocked += 1
            continue
        if not allow_changes:
            continue
        filt = {'_id': existing['_id']} if existing else {'_id': int(cik)}
        # Do not modify the historical financial data or reclassify profiles as successfully collected.
        db.companies.update_one(filt, {'$set': {**p, 'universe_snapshot_id': snapshot_id,
                              'universe_discovered_at': now, 'updated_at': now}}, upsert=True)
        if existing: updated += 1
        else: inserted += 1
    return {'inserted': inserted, 'updated': updated, 'blocked': blocked}


def choose_batch(db, profiles, batch_size, snapshot_id):
    """Cursor advances across the full universe; avoids first-N starvation."""
    key = 'blackrock_etf_collection_cursor'
    state = db.universe_sync_state.find_one({'_id': key}) or {}
    start = int(state.get('next_offset', 0)) if state.get('snapshot_id') == snapshot_id else 0
    if start >= len(profiles): start = 0
    batch = profiles[start:start+batch_size]
    return key, start, batch


def collection_plan(start, total, batch_size):
    """Plan the next contiguous batch without wrapping at universe completion."""
    if not 0 <= start <= total or batch_size < 1:
        raise ValueError('Invalid collection checkpoint or batch size')
    return start, min(start + batch_size, total)


def record_batch(db, key, snapshot_id, next_offset, total, result):
    db.universe_sync_state.update_one({'_id': key}, {'$set': {
        'snapshot_id': snapshot_id, 'next_offset': next_offset,
        'total': total, 'updated_at': datetime.now(timezone.utc),
        'last_batch_counts': result}}, upsert=True)


def set_action_outputs(continuation, offset, total):
    output = os.getenv('GITHUB_OUTPUT')
    if output:
        with open(output, 'a', encoding='utf-8') as handle:
            handle.write(f'continuation={str(continuation).lower()}\n')
            handle.write(f'next_offset={offset}\n')
            handle.write(f'total={total}\n')


def main():
    p = argparse.ArgumentParser(description='Synchronize ETF company profiles and collect resumable SEC batches')
    p.add_argument('--holdings-file', default='data/blackrock_holdings_2026-11-24.csv')
    p.add_argument('--market-cap-file', default=None, help='Optional verified $10B+ screen; no implied market cap without this')
    p.add_argument('--batch-size', type=int, default=30)
    p.add_argument('--refresh-days', type=int, default=7)
    p.add_argument('--years', type=int, default=5)
    p.add_argument('--sync-only', action='store_true')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--full-collection', action='store_true', help='Automatically process successive batches')
    p.add_argument('--max-runtime-seconds', type=int, default=6300, help='Time budget for full collection; leaves time to dispatch continuation')
    a = p.parse_args()
    if a.batch_size < 1: p.error('batch-size must be positive')
    if a.max_runtime_seconds < 60: p.error('max-runtime-seconds must be >= 60')
    if a.sync_only and a.full_collection: p.error('sync-only and full-collection cannot be combined')
    started = time.monotonic()
    if not os.getenv('MONGODB_URI'): p.error('MONGODB_URI missing')
    if not os.getenv('SEC_USER_AGENT'): p.error('SEC_USER_AGENT missing')
    sec = SecClient(os.environ['SEC_USER_AGENT'])
    official = sec_map(sec)
    profiles, unmatched, conflicts = build_universe(a.holdings_file, official, a.market_cap_file)
    raw = Path(a.holdings_file).read_bytes()
    cap_raw = Path(a.market_cap_file).read_bytes() if a.market_cap_file else b''
    snapshot_id = hashlib.sha256(raw + b'\x00' + cap_raw).hexdigest()
    with MongoClient(os.environ['MONGODB_URI'], tz_aware=True, serverSelectionTimeoutMS=15000) as client:
        client.admin.command('ping')
        db = client[os.getenv('MONGODB_DATABASE', 'maketdata')]
        stats = sync_profiles(db, profiles, snapshot_id, allow_changes=not a.dry_run)
        key, start, batch = choose_batch(db, profiles, a.batch_size, snapshot_id)
        print('UNIVERSE_SYNC', json.dumps({'eligible_sec_issuers': len(profiles),
              'unmatched_tickers': len(unmatched), 'identity_conflicts': conflicts[:30],
              'snapshot_id': snapshot_id, 'profiles': stats, 'batch_offset': start,
              'batch_size': len(batch), 'market_cap_verified': bool(a.market_cap_file)}), flush=True)
        if a.dry_run or a.sync_only:
            return
        # The initial offset is computed once; a full run keeps moving forward.
        total = len(profiles)
        if a.full_collection:
            state = db.universe_sync_state.find_one({'_id': key}) or {}
            if state.get('snapshot_id') == snapshot_id and int(state.get('next_offset', 0)) >= total:
                print('FULL_COLLECTION_ALREADY_COMPLETE', json.dumps({'total': total}), flush=True)
                set_action_outputs(False, total, total)
                return
        offset = start
        batches = 0
        successes = skips = 0
        while offset < total:
            # Reserve enough time for another job to be dispatched by GitHub Actions.
            if a.full_collection and batches > 0 and time.monotonic() - started >= a.max_runtime_seconds:
                break
            _, end = collection_plan(offset, total, a.batch_size)
            selected = profiles[offset:end]
            # Refuse to advance past identity conflicts; otherwise issuers are silently lost.
            blocked = [x['ticker'] for x in selected if not db.companies.find_one({'ticker': x['ticker'], 'cik': x['cik']})]
            if blocked:
                raise RuntimeError(f'Batch contains blocked/missing issuer profiles; cursor not advanced: {blocked}')
            result = run(db, sec, len(selected), a.refresh_days, a.years, 10_000_000_000,
                         tickers=[x['ticker'] for x in selected], universe_mode='blackrock_holdings',
                         universe_file=a.holdings_file)
            if result['failed']:
                raise RuntimeError(f'Batch has {result["failed"]} failed issuers; cursor not advanced')
            # Commit checkpoint only after a successful batch.
            offset = end
            record_batch(db, key, snapshot_id, offset, total, result)
            batches += 1
            successes += result['success']
            skips += result['skipped']
            print('BATCH_COMPLETE', json.dumps({'next_offset': offset, 'total': total, 'result': result}, default=str), flush=True)
            if not a.full_collection:
                break
        continuation = a.full_collection and offset < total
        print('COLLECTION_SUMMARY', json.dumps({'batches': batches, 'success': successes,
              'skipped': skips, 'next_offset': offset, 'total': total,
              'continuation_required': continuation}), flush=True)
        set_action_outputs(continuation, offset, total)

if __name__ == '__main__':
    main()
