"""v4.1.0 (2026-11-24): SEC EDGAR via sec-edgar-api; EdgarTools summary; MongoDB upserts."""
import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import requests
from pymongo import MongoClient, UpdateOne
from sec_edgar_api import EdgarClient

SEC_TICKERS = 'https://www.sec.gov/files/company_tickers_exchange.json'
DEFAULT_TICKERS = 'AAPL,MSFT,GOOGL,AMZN,NVDA,META,BRK-B,JPM,JNJ,XOM'


def now():
    return datetime.now(timezone.utc)


def parse_universe(payload):
    fields = payload['fields']
    return [dict(zip(fields, row)) for row in payload['data']]


def universe(user_agent):
    response = requests.get(SEC_TICKERS, headers={'User-Agent': user_agent, 'Accept-Encoding': 'gzip, deflate'}, timeout=40)
    response.raise_for_status()
    return parse_universe(response.json())


def is_due(state, days):
    current = now()
    if state and state.get('next_retry_at') and state['next_retry_at'] > current:
        return False
    last = (state or {}).get('last_success_at')
    return last is None or last <= current - timedelta(days=days)


def flatten_facts(payload, cik):
    """One document per SEC taxonomy/concept/unit, not one giant company document."""
    for taxonomy, concepts in payload.get('facts', {}).items():
        for concept, record in concepts.items():
            for unit, entries in record.get('units', {}).items():
                doc_id = f'{cik}:{taxonomy}:{concept}:{unit}'
                yield {'_id': doc_id, 'cik': cik, 'taxonomy': taxonomy, 'concept': concept,
                       'unit': unit, 'label': record.get('label'),
                       'description': record.get('description'), 'observations': entries}


def financial_summary(ticker, user_agent):
    """Optional EdgarTools enrichment; failure does not block raw SEC ingestion."""
    try:
        from edgar import Company, set_identity
        set_identity(user_agent)
        financials = Company(ticker).get_financials()
        if financials is None:
            return {'status': 'unavailable'}
        result = {'status': 'ok'}
        for key, method in [('revenue', 'get_revenue'), ('net_income', 'get_net_income')]:
            try:
                value = getattr(financials, method)()
                result[key] = float(value) if value is not None else None
            except (AttributeError, TypeError, ValueError):
                result[key] = None
        return result
    except Exception as exc:
        return {'status': 'error', 'error': f'{type(exc).__name__}: {exc}'[:300]}


def collect(db, edgar, rows, refresh_days, with_summary, user_agent):
    db.companies.create_index('ticker')
    db.sec_facts.create_index([('cik', 1), ('taxonomy', 1), ('concept', 1)])
    db.collection_state.create_index('next_retry_at')
    run_id = str(uuid4())
    db.pipeline_runs.insert_one({'_id': run_id, 'started_at': now(), 'status': 'running'})
    stats = {'requested': len(rows), 'success': 0, 'skipped': 0, 'failed': 0, 'concept_documents': 0}
    try:
        for row in rows:
            cik = int(row['cik'])
            ticker = row['ticker']
            db.companies.update_one({'_id': cik}, {'$set': {'name': row['name'], 'ticker': ticker, 'exchange': row.get('exchange'), 'updated_at': now()}}, upsert=True)
            state = db.collection_state.find_one({'_id': cik})
            if not is_due(state, refresh_days):
                stats['skipped'] += 1
                print(f'SKIP {ticker} (fresh or retry cooldown)', flush=True)
                continue
            try:
                payload = edgar.get_company_facts(cik=str(cik))
                if int(payload.get('cik', -1)) != cik or not isinstance(payload.get('facts'), dict):
                    raise ValueError('Invalid SEC Company Facts payload')
                docs = list(flatten_facts(payload, cik))
                if not docs:
                    raise ValueError('No SEC facts returned')
                # Upsert each concept/unit separately; preserve all SEC observation metadata.
                for i in range(0, len(docs), 100):
                    operations = [UpdateOne({'_id': doc['_id']}, {'$set': {**doc, 'updated_at': now()}}, upsert=True) for doc in docs[i:i+100]]
                    db.sec_facts.bulk_write(operations, ordered=False)
                # Remove concepts that no longer appear in the latest SEC response.
                ids = [d['_id'] for d in docs]
                db.sec_facts.delete_many({'cik': cik, '_id': {'$nin': ids}})
                if with_summary:
                    db.financial_summaries.update_one({'_id': cik}, {'$set': {'ticker': ticker, **financial_summary(ticker, user_agent), 'updated_at': now()}}, upsert=True)
                db.collection_state.update_one({'_id': cik}, {'$set': {'last_success_at': now(), 'next_retry_at': None, 'failures': 0, 'last_error': None, 'concept_count': len(docs)}}, upsert=True)
                stats['success'] += 1
                stats['concept_documents'] += len(docs)
                print(f'OK {ticker} CIK={cik} concepts={len(docs)}', flush=True)
            except Exception as exc:
                failures = int((state or {}).get('failures', 0)) + 1
                retry = now() + timedelta(hours=min(2 ** min(failures, 6), 48))
                db.collection_state.update_one({'_id': cik}, {'$set': {'failures': failures, 'next_retry_at': retry, 'last_error': f'{type(exc).__name__}: {exc}'[:400]}}, upsert=True)
                stats['failed'] += 1
                print(f'FAIL {ticker}: {type(exc).__name__}: {exc}', flush=True)
            time.sleep(0.2)
        status = 'completed' if not stats['failed'] else 'completed_with_errors'
    except Exception:
        db.pipeline_runs.update_one({'_id': run_id}, {'$set': {'finished_at': now(), 'status': 'failed', 'stats': stats}})
        raise
    db.pipeline_runs.update_one({'_id': run_id}, {'$set': {'finished_at': now(), 'status': status, 'stats': stats}})
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tickers', default=DEFAULT_TICKERS)
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--refresh-days', type=int, default=7)
    parser.add_argument('--with-edgartools-summary', action='store_true')
    args = parser.parse_args()
    if args.limit < 1 or args.refresh_days < 0:
        parser.error('limit must be >=1 and refresh-days >=0')
    uri = os.environ.get('MONGODB_URI')
    agent = os.environ.get('SEC_USER_AGENT')
    if not uri or not agent or '@' not in agent:
        parser.error('Set MONGODB_URI and SEC_USER_AGENT (include real contact email)')
    rows = universe(agent)
    by_ticker = {r['ticker'].upper(): r for r in rows}
    requested = [t.strip().upper() for t in args.tickers.split(',') if t.strip()]
    selected = []
    for ticker in requested:
        row = by_ticker.get(ticker)
        if row and row['cik'] not in {x['cik'] for x in selected}:
            selected.append(row)
        elif not row:
            print(f'WARN {ticker} not found in SEC exchange universe', flush=True)
        if len(selected) >= args.limit:
            break
    if not selected:
        parser.error('No requested tickers found in SEC universe')
    client = MongoClient(uri, serverSelectionTimeoutMS=15000)
    try:
        client.admin.command('ping')
        db = client[os.environ.get('MONGODB_DATABASE', 'maketdata')]
        stats = collect(db, EdgarClient(user_agent=agent), selected, args.refresh_days, args.with_edgartools_summary, agent)
        print(json.dumps(stats, indent=2))
        if stats['failed'] or not (stats['success'] or stats['skipped']):
            raise SystemExit(1)
    finally:
        client.close()


if __name__ == '__main__':
    main()
