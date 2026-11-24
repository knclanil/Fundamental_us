"""Market research ETL v3.2.1 (2026-11-24).
Changelog: v3.1.3 ETF classification, recoverable error queue, durable failed-run commits; v3.1.2 workflow-controlled batch size; v3.1.1 security filtering, expected 404 skips, durable rotation; v3.1.0 rotation; v3.0.5 dtype fix.
Does not bypass source access restrictions."""
import argparse
import hashlib
import io
import json
import os
import re
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.robotparser import RobotFileParser

import duckdb
import pandas as pd
import requests
from finviz import parse_finviz_snapshot, parse_finviz_profile, is_fund_snapshot
try:
    from .priority import select_batch
    from .alpha_vantage import enrich_caps
except ImportError:
    from priority import select_batch
    from alpha_vantage import enrich_caps
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
NASDAQ = 'https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt'
OTHER = 'https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt'
BASE = 'https://stockanalysis.com/stocks/{}/'
PAGES = {'statistics': 'statistics/', 'income': 'financials/', 'balance': 'financials/balance-sheet/',
         'cashflow': 'financials/cash-flow-statement/', 'ratios': 'financials/ratios/'}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def symbol_slug(ticker):
    return ticker.lower().replace('.', '-')


def fetch(session, url, delay, timeout):
    time.sleep(delay)
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def parse_exchange(text, symbol_col):
    lines = [x for x in text.splitlines() if x and not x.startswith('File Creation Time')]
    df = pd.read_csv(io.StringIO('\n'.join(lines)), sep='|', dtype=str).fillna('')
    if symbol_col not in df.columns:
        raise ValueError('Exchange symbol directory schema changed')
    df = df[df[symbol_col].str.fullmatch(r'[A-Za-z][A-Za-z0-9.\-]*', na=False)]
    if 'Test Issue' in df.columns:
        df = df[df['Test Issue'] != 'Y']
    if 'ETF' in df.columns:
        df = df[df['ETF'].str.strip().str.upper() != 'Y']
    if 'Financial Status' in df.columns:
        df = df[df['Financial Status'] != 'D']
    if 'Security Name' not in df.columns:
        raise ValueError('Missing Security Name column')
    # These directories include non-common securities; exclude obvious types and flag remaining for review.
    reject = r'\b(?:warrants?|rights?|units?|preferred|preference|depositary shares?|notes due|bonds?|debentures?|etns?|funds?|trusts?|exchange.traded|index ETF|ETF|ETP)\b'
    df = df[~df['Security Name'].str.contains(reject, case=False, regex=True, na=False)]
    # NASDAQ directory: NextShares (N) and ETF (Y) are not operating-company common shares.
    if 'NextShares' in df.columns:
        df = df[df['NextShares'] != 'Y']
    # Some unit/warrant listings omit their security type in the name; FINVIZ 404s
    # are handled explicitly downstream instead of guessing from ticker suffixes.
    return pd.DataFrame({'ticker': df[symbol_col].str.upper(), 'company_name': df['Security Name'],
                         'exchange': df['Listing Exchange'] if 'Listing Exchange' in df else 'NASDAQ'})


def collect_universe(session, cfg):
    if cfg['universe'] == 'custom':
        df = pd.read_csv(ROOT / 'config' / 'tickers.csv', dtype=str).fillna('')
        if 'ticker' not in df:
            raise ValueError('Custom universe needs ticker column')
        for col in ['company_name', 'exchange']:
            if col not in df:
                df[col] = ''
        df = df[['ticker', 'company_name', 'exchange']]
    elif cfg['universe'] in ('dynamic', 'exchange'):
        a = fetch(session, NASDAQ, cfg['request_delay_seconds'], cfg['timeout_seconds'])
        b = fetch(session, OTHER, cfg['request_delay_seconds'], cfg['timeout_seconds'])
        df = pd.concat([parse_exchange(a, 'Symbol'), parse_exchange(b, 'ACT Symbol')], ignore_index=True)
    else:
        raise ValueError('universe must be custom or dynamic')
    df = df.drop_duplicates('ticker').sort_values('ticker').reset_index(drop=True)
    if len(df) < 1:
        raise ValueError('Universe empty; previous state retained')
    return df


def parse_statistics(html, ticker, timestamp):
    soup = BeautifulSoup(html, 'lxml')
    rows = []
    for table in soup.select('table'):
        section = table.find_previous(['h2', 'h3'])
        category = section.get_text(' ', strip=True) if section else 'Uncategorized'
        for tr in table.select('tr'):
            cells = tr.find_all(['td', 'th'], recursive=False)
            if len(cells) != 2:
                continue
            label, val = [c.get_text(' ', strip=True) for c in cells]
            if label and val and label.lower() not in ('name', 'metric'):
                rows.append(dict(ticker=ticker, category=category, metric=label, raw_value=val,
                                 observed_at=timestamp, source_page='statistics'))
    return rows


def parse_financials(html, ticker, statement, timestamp):
    """Parse period headers and rows without guessing period meaning or numeric scaling."""
    soup = BeautifulSoup(html, 'lxml')
    rows = []
    for table in soup.select('table'):
        trs = table.select('tr')
        if not trs:
            continue
        head = [c.get_text(' ', strip=True) for c in trs[0].find_all(['th', 'td'], recursive=False)]
        if len(head) < 2:
            continue
        for tr in trs[1:]:
            cells = tr.find_all(['th', 'td'], recursive=False)
            if len(cells) < 2:
                continue
            metric = cells[0].get_text(' ', strip=True)
            for i, cell in enumerate(cells[1:], 1):
                if i >= len(head) or not metric:
                    continue
                period = head[i]
                value = cell.get_text(' ', strip=True)
                if period and value and value not in ('-', '—'):
                    rows.append(dict(ticker=ticker, statement=statement, metric=metric, period_label=period,
                                     raw_value=value, observed_at=timestamp, source_page=statement))
    return rows


def parse_profile(html):
    """Best-effort only; industry/sector may be absent and should remain null, not fabricated."""
    soup = BeautifulSoup(html, 'lxml')
    text = soup.get_text(' ', strip=True)
    result = {}
    for key in ('Sector', 'Industry'):
        match = re.search(r'\b' + key + r'\s+(.{2,90}?)\s+(?:Industry|Sector|Country|Stock Exchange|Full Time Employees|Website|IPO Date)\b', text)
        result[key.lower()] = match.group(1).strip() if match else None
    return result


def robots_allowed(session, url, agent):
    from urllib.parse import urlsplit
    parsed = urlsplit(url)
    robots_url = f'{parsed.scheme}://{parsed.netloc}/robots.txt'
    r = session.get(robots_url, timeout=20)
    r.raise_for_status()
    parser = RobotFileParser()
    parser.parse(r.text.splitlines())
    return parser.can_fetch(agent, url)


def load_existing(path):
    if path.exists():
        return duckdb.sql(f"SELECT * FROM read_parquet('{path.as_posix()}')").df()
    return pd.DataFrame()


def write_parquet(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp.parquet')
    df.to_parquet(temp, index=False, compression='zstd')
    temp.replace(path)


def merge_records(path, incoming, keys, keep_revisions=False):
    if not incoming:
        return 0
    new = pd.DataFrame(incoming)
    old = load_existing(path)
    if not old.empty:
        new = pd.concat([old, new], ignore_index=True)
    if keep_revisions:
        # Preserve changed source values while eliminating exact repeated observations.
        keys = keys + ['raw_value']
    new = new.sort_values('observed_at').drop_duplicates(keys, keep='last')
    write_parquet(new, path)
    return len(incoming)


def update_universe(current, mode="dynamic"):
    path = DATA / 'dimensions' / 'instruments.parquet'
    old = load_existing(path)
    now = utc_now()
    current = current.copy()
    current_tickers = current.ticker.tolist()
    current['instrument_id'] = current['ticker'].map(lambda s: hashlib.sha256(s.encode()).hexdigest()[:16])
    current['is_active'] = True
    current['first_seen'] = now
    current['last_seen'] = now
    current['sector'] = pd.Series(pd.NA, index=current.index, dtype='string')
    current['industry'] = pd.Series(pd.NA, index=current.index, dtype='string')
    if not old.empty:
        if mode != 'custom' and len(old) >= 100 and len(current) < int(len(old) * 0.65):
            raise ValueError(f'Universe shrank unexpectedly ({len(old)} -> {len(current)}); refusing dimension overwrite')
        by_ticker = old.set_index('ticker')
        for idx, row in current.iterrows():
            t = row['ticker']
            if t in by_ticker.index:
                for field in ['instrument_id', 'first_seen', 'sector', 'industry']:
                    current.at[idx, field] = by_ticker.loc[t, field]
        # Do not deactivate on one missing snapshot; flag for review.
        missing = old[~old.ticker.isin(current.ticker)].copy()
        missing['is_active'] = old.loc[missing.index, 'is_active'].values if mode == 'custom' else False  # NOT confirmed delisted
        if not missing.empty:
            for col in ('sector', 'industry'):
                missing[col] = missing[col].astype('string')
            current = pd.concat([current, missing.reindex(columns=current.columns)], ignore_index=True)
    for column in ('sector', 'industry'):
        current[column] = current[column].astype('string')
    write_parquet(current, path)
    return current[current.ticker.isin(set(current_tickers))] if mode == "custom" else current[current.is_active]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', default=str(ROOT / 'config/settings.json'))
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    if args.dry_run:
        print(json.dumps({'pages': PAGES, 'config': cfg, 'note': 'No network calls made'}, indent=2))
        return
    if not cfg['allow_automated_collection']:
        raise SystemExit('Automated collection is disabled. Verify provider permission, then set allow_automated_collection=true in config/settings.json.')
    print('Automated collection enabled.')
    print(f"Universe: {cfg.get('universe')}")
    print(f"Maximum tickers: {cfg.get('max_tickers')}")
    print(f"Request delay: {cfg.get('request_delay_seconds')} seconds")
    if 'YOUR_EMAIL' in cfg['contact_user_agent']:
        raise SystemExit('Set a real contact address in contact_user_agent.')
    session = requests.Session()
    session.headers.update({'User-Agent': cfg['contact_user_agent']})
    try:
        universe = collect_universe(session, cfg)
        allowed = ([BASE.format('mu') + suffix for suffix in PAGES.values()] + [BASE.format('mu')]) if cfg.get('collect_stockanalysis', True) else []
        if cfg.get('collect_finviz', False):
            allowed.append('https://finviz.com/quote.ashx?t=MU')
        for url in allowed:
            if not robots_allowed(session, url, cfg['contact_user_agent']):
                raise SystemExit(f'robots.txt disallows collection: {url}')
        active = update_universe(universe, cfg["universe"])
        limit = int(os.environ.get('MARKET_MAX_TICKERS', cfg.get('max_tickers', 0)))
        if limit <= 0 and os.environ.get('MARKET_MAX_TICKERS'):
            raise SystemExit('MARKET_MAX_TICKERS must be a positive integer')
        total_active = len(active)
        cursor_path = DATA / 'state' / 'cursor.json'
        cursor = 0
        rotate = bool(cfg.get('rotate_tickers', False))
        priority_mode = cfg.get('collection_strategy') == 'market_cap_priority'
        if priority_mode:
            if cfg.get('alpha_vantage_enabled', True):
                # Spend free calls only on unknown caps; do not repeatedly query
                # companies with known FINVIZ or seed market capitalizations.
                try:
                    from priority import cap_lookup
                except ImportError:
                    from .priority import cap_lookup
                cache_file = DATA / 'state' / 'alpha_market_caps.json'
                known = cap_lookup(DATA / 'finviz' / 'snapshots.parquet',
                    ROOT / cfg.get('market_cap_seed_csv', 'config/market_caps.csv'), cache_file)
                unknown = [str(t) for t in active.ticker if str(t).upper() not in known]
                enrich_caps(unknown, cache_file, DATA / 'state' / 'alpha_quota.json',
                    daily_limit=int(cfg.get('alpha_vantage_daily_budget', 20)),
                    timeout=int(cfg.get('timeout_seconds', 30)),
                    delay=float(cfg.get('alpha_vantage_delay_seconds', 1)))
            if limit <= 0:
                raise SystemExit('Market-cap priority requires a positive batch size')
            active, selection = select_batch(
                active, DATA / 'finviz' / 'snapshots.parquet',
                ROOT / cfg.get('market_cap_seed_csv', 'config/market_caps.csv'),
                limit, int(cfg.get('refresh_after_hours', 24)),
                DATA / 'state' / 'failed_tickers.json',
                alpha_cache_path=DATA / 'state' / 'alpha_market_caps.json')
            print(f"Priority selection: {selection}; unknown caps require a seed feed", flush=True)
        elif rotate and limit > 0 and total_active > limit:
            if cursor_path.exists():
                try:
                    cursor = int(json.loads(cursor_path.read_text()).get('next_offset', 0)) % total_active
                except (ValueError, TypeError, json.JSONDecodeError):
                    cursor = 0
            indices = [(cursor + i) % total_active for i in range(limit)]
            active = active.iloc[indices].copy()
        elif limit > 0:
            active = active.head(limit)
        print(f'Universe size: {total_active}; selected: {len(active)}; rotation offset: {cursor}', flush=True)
        log = []
        for _, item in active.iterrows():
            ticker = item['ticker']
            base = BASE.format(symbol_slug(ticker))
            if cfg.get('collect_stockanalysis', True):
              try:
                profile_html = fetch(session, base, cfg['request_delay_seconds'], cfg['timeout_seconds'])
                profile = parse_profile(profile_html)
                instruments = load_existing(DATA / 'dimensions/instruments.parquet')
                for column in ('sector', 'industry'):
                    instruments[column] = instruments[column].astype('string')
                mask = instruments.ticker == ticker
                for key in ['sector', 'industry']:
                    if profile[key]:
                        instruments.loc[mask, key] = profile[key]
                write_parquet(instruments, DATA / 'dimensions/instruments.parquet')
              except requests.RequestException as exc:
                log.append({'ticker': ticker, 'page': 'profile', 'status': 'error', 'detail': str(exc)[:300], 'at': utc_now()})
            if cfg.get('collect_finviz', False):
                from urllib.parse import quote
                finviz_url = 'https://finviz.com/stock?t=' + quote(ticker, safe='') + '&p=d'
                try:
                    html = fetch(session, finviz_url, cfg['request_delay_seconds'], cfg['timeout_seconds'])
                    now = utc_now()
                    if is_fund_snapshot(html):
                        print(f'[SKIP] {ticker} | finviz | ETF/fund snapshot (not common stock)', flush=True)
                        log.append({'ticker': ticker, 'page': 'finviz', 'status': 'skipped',
                                    'detail': 'ETF/fund snapshot (not common stock)', 'at': now})
                        continue
                    rows = parse_finviz_snapshot(html, ticker, now)
                    print(f'[OK] {ticker} | finviz | {len(rows)} metrics extracted', flush=True)
                    required = set(cfg.get('finviz_required_metrics', ['Price', 'Market Cap', 'Volume']))
                    found = {r['metric'] for r in rows}
                    missing = required - found
                    if missing:
                        raise ValueError(f'FINVIZ quality check failed; missing metrics: {sorted(missing)}')
                    minimum = int(cfg.get('finviz_min_metrics', 60))
                    if len(found) < minimum:
                        raise ValueError(f'FINVIZ quality check failed; {len(found)} unique metrics < {minimum}')
                    count = merge_records(DATA / 'finviz' / 'snapshots.parquet', rows,
                                          ['ticker', 'metric'], keep_revisions=True)
                    profile = parse_finviz_profile(html)
                    instruments = load_existing(DATA / 'dimensions/instruments.parquet')
                    if not instruments.empty and 'ticker' in instruments:
                        for column in ('sector', 'industry'):
                            if column not in instruments.columns:
                                instruments[column] = pd.Series(pd.NA, index=instruments.index, dtype='string')
                            else:
                                instruments[column] = instruments[column].astype('string')
                        mask = instruments.ticker == ticker
                        for key in ('sector', 'industry'):
                            if profile[key] and key in instruments:
                                instruments.loc[mask, key] = profile[key]
                        write_parquet(instruments, DATA / 'dimensions/instruments.parquet')
                    log.append({'ticker': ticker, 'page': 'finviz', 'status': 'ok',
                                'detail': str(count), 'at': now})
                except requests.HTTPError as exc:
                    if exc.response is not None and exc.response.status_code == 404:
                        print(f'[SKIP] {ticker} | finviz | HTTP 404: symbol not available at provider', flush=True)
                        log.append({'ticker': ticker, 'page': 'finviz', 'status': 'skipped',
                                    'detail': 'HTTP 404: symbol not available at provider', 'at': utc_now()})
                    else:
                        print(f'[ERROR] {ticker} | finviz | {type(exc).__name__}: {exc}', flush=True)
                        traceback.print_exc()
                        log.append({'ticker': ticker, 'page': 'finviz', 'status': 'error',
                                    'detail': str(exc)[:300], 'at': utc_now()})
                except Exception as exc:
                    print(f'[ERROR] {ticker} | finviz | {type(exc).__name__}: {exc}', flush=True)
                    traceback.print_exc()
                    log.append({'ticker': ticker, 'page': 'finviz', 'status': 'error',
                                'detail': str(exc)[:300], 'at': utc_now()})
            for name, suffix in (PAGES.items() if cfg.get('collect_stockanalysis', True) else []):
                if name == 'statistics' and not cfg['collect_statistics']:
                    continue
                if name != 'statistics' and not cfg['collect_financials']:
                    continue
                try:
                    html = fetch(session, base + suffix, cfg['request_delay_seconds'], cfg['timeout_seconds'])
                    now = utc_now()
                    rows = parse_statistics(html, ticker, now) if name == 'statistics' else parse_financials(html, ticker, name, now)
                    if not rows:
                        raise ValueError('No table rows parsed: verify page structure or access')
                    if name == 'statistics':
                        path = DATA / 'statistics' / 'changes.parquet'
                        count = merge_records(path, rows, ['ticker', 'category', 'metric'], keep_revisions=True)
                    else:
                        path = DATA / 'financials' / 'observations.parquet'
                        count = merge_records(path, rows, ['ticker', 'statement', 'metric', 'period_label'], keep_revisions=True)
                    log.append({'ticker': ticker, 'page': name, 'status': 'ok', 'detail': str(count), 'at': now})
                except Exception as exc:
                    print(f'[ERROR] {ticker} | {name} | {type(exc).__name__}: {exc}', flush=True)
                    traceback.print_exc()
                    log.append({'ticker': ticker, 'page': name, 'status': 'error', 'detail': str(exc)[:300], 'at': utc_now()})
        # Save a human-readable log that can be uploaded even when the job fails.
        DATA.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(log, columns=['ticker','page','status','detail','at']).to_csv(DATA / 'execution_log_latest.csv', index=False)
        for entry in log:
            print(f"[RESULT] {entry['ticker']} | {entry['page']} | {entry['status']} | {entry['detail']}", flush=True)
        log_path = DATA / 'execution_log.parquet'
        existing = load_existing(log_path)
        combined = pd.concat([existing, pd.DataFrame(log)], ignore_index=True)
        write_parquet(combined, log_path)
        errors = sum(x['status'] == 'error' for x in log)
        print(f'Processed {len(active)} tickers; {errors} page failures')
        successes = sum(x['status'] == 'ok' for x in log)
        skips = sum(x['status'] == 'skipped' for x in log)
        print(f'Pages successful: {successes}; unsupported skips: {skips}; unexpected failures: {errors}', flush=True)
        # Persist a durable retry queue even if the job ultimately fails.
        retry_path = DATA / 'state' / 'failed_tickers.json'
        retry_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            retry_state = json.loads(retry_path.read_text()) if retry_path.exists() else {}
            if not isinstance(retry_state, dict):
                retry_state = {}
        except (OSError, ValueError, TypeError):
            retry_state = {}
        for entry in log:
            key = f"{entry['ticker']}|{entry['page']}"
            if entry['status'] == 'error':
                retry_state[key] = {'ticker': entry['ticker'], 'page': entry['page'],
                                    'detail': entry['detail'], 'last_failed_at': entry['at']}
            elif entry['status'] == 'ok':
                retry_state.pop(key, None)
            elif entry['status'] == 'skipped':
                retry_state.pop(key, None)
        retry_path.write_text(json.dumps(retry_state, indent=2, sort_keys=True) + '\n')
        print(f'Retry queue entries: {len(retry_state)}', flush=True)
        # The current batch was attempted. Advance the cursor so the next
        # scheduled run does not waste hours on the same successful tickers.
        # Failures are recorded in failed_tickers.json for explicit retry.
        if not priority_mode and rotate and limit > 0 and total_active > limit:
            cursor_path.parent.mkdir(parents=True, exist_ok=True)
            cursor_path.write_text(json.dumps({'next_offset': (cursor + len(active)) % total_active,
                                               'universe_size': total_active,
                                               'updated_at': utc_now()}, indent=2) + '\n')
        if (not log and not priority_mode) or (successes == 0 and len(active) > 0 and skips == 0) or errors:
            print(f'Batch checkpoint saved; {errors} errors remain in retry queue.', flush=True)
            raise SystemExit(1)
        print(f'Quality gate passed: {successes} successful pages; {skips} expected skips; {errors} errors', flush=True)

    finally:
        session.close()

if __name__ == '__main__':
    main()
