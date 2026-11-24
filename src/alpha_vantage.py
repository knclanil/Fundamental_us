"""v3.2.1 (2026-11-24): quota-bounded Alpha Vantage OVERVIEW enrichment.
Only reads the key from the environment; never logs it. Free-tier default: 20/day.
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

ENDPOINT = 'https://www.alphavantage.co/query'

def _read(path, default):
    try:
        value = json.loads(Path(path).read_text())
        return value if isinstance(value, dict) else default
    except (OSError, ValueError, TypeError):
        return default

def enrich_caps(tickers, cache_path, quota_path, *, daily_limit=20, timeout=30,
                delay=1, session=None, now=None):
    """Fetch at most daily_limit OVERVIEW requests per UTC day, across batches.

    Cache and quota files are written after each request. Never retries an API
    response that indicates a provider limit; defer remaining tickers.
    """
    cache_path, quota_path = Path(cache_path), Path(quota_path)
    cache = _read(cache_path, {})
    quota = _read(quota_path, {})
    today = (now or datetime.now(timezone.utc)).date().isoformat()
    if quota.get('utc_date') != today:
        quota = {'utc_date': today, 'requests_used': 0}
    key = os.environ.get('ALPHA_VANTAGE_API_KEY', '').strip()
    if not key:
        print('[ALPHA] No ALPHA_VANTAGE_API_KEY; using existing market caps only.', flush=True)
        return cache
    limit = max(0, min(int(daily_limit), 25))
    client = session or requests.Session()
    try:
        for ticker in dict.fromkeys(str(t).upper() for t in tickers):
            if ticker in cache or int(quota['requests_used']) >= limit:
                continue
            # Count *before* network access to avoid quota overspend on exceptions.
            quota['requests_used'] = int(quota['requests_used']) + 1
            quota_path.parent.mkdir(parents=True, exist_ok=True)
            quota_path.write_text(json.dumps(quota, indent=2) + '\n')
            try:
                response = client.get(ENDPOINT, params={'function': 'OVERVIEW',
                    'symbol': ticker, 'apikey': key}, timeout=timeout)
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise ValueError('Unexpected OVERVIEW response')
                if any(field in payload for field in ('Note', 'Information', 'Error Message')):
                    print(f'[ALPHA] Provider notice for {ticker}; stopping enrichment.', flush=True)
                    break
                cap = payload.get('MarketCapitalization')
                if cap is not None and str(cap).isdigit() and int(cap) > 0:
                    cache[ticker] = {'market_cap_usd': int(cap), 'updated_at':
                        datetime.now(timezone.utc).isoformat(), 'source': 'alpha_vantage'}
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True) + '\n')
                    print(f'[ALPHA] Classified {ticker}', flush=True)
                else:
                    # Mark unavailable, so we don't repeatedly spend free calls.
                    cache[ticker] = {'market_cap_usd': None, 'updated_at':
                        datetime.now(timezone.utc).isoformat(), 'source': 'alpha_vantage'}
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True) + '\n')
                    print(f'[ALPHA] No capitalization available for {ticker}', flush=True)
            except (requests.RequestException, ValueError) as exc:
                print(f'[ALPHA] Request failed for {ticker}: {type(exc).__name__}', flush=True)
                break
            if delay:
                time.sleep(delay)
    finally:
        if session is None:
            client.close()
    print(f"[ALPHA] UTC {today}: {quota['requests_used']}/{limit} calls used", flush=True)
    return cache
