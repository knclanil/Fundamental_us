"""Market research ETL v3.0.3 (2026-11-23).
Changelog: v3.0.3 actionable per-ticker diagnostics and durable failure logs; v3.0.0 FINVIZ integration.
Does not bypass source access restrictions. Financial page HTML structure must be validated live.
"""
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
from finviz import parse_finviz_snapshot, parse_finviz_profile
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
        df = df[df['ETF'] != 'Y']
    if 'Financial Status' in df.columns:
        df = df[df['Financial Status'] != 'D']
    if 'Security Name' not in df.columns:
        raise ValueError('Missing Security Name column')
    # These directories include non-common securities; exclude obvious types and flag remaining for review.
    reject = r'\b(warrant|right|unit|preferred|depositary share|notes due|bond|debenture|etn|fund|trust)\b'
    df = df[~df['Security Name'].str.contains(reject, case=False, regex=True, na=False)]
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
    else:
        a = fetch(session, NASDAQ, cfg['request_delay_seconds'], cfg['timeout_seconds'])
        b = fetch(session, OTHER, cfg['request_delay_seconds'], cfg['timeout_seconds'])
        df = pd.concat([parse_exchange(a, 'Symbol'), parse_exchange(b, 'ACT Symbol')], ignore_index=True)
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


def update_universe(current):
    path = DATA / 'dimensions' / 'instruments.parquet'
    old = load_existing(path)
    now = utc_now()
    current = current.copy()
    current['instrument_id'] = current['ticker'].map(lambda s: hashlib.sha256(s.encode()).hexdigest()[:16])
    current['is_active'] = True
    current['first_seen'] = now
    current['last_seen'] = now
    current['sector'] = None
    current['industry'] = None
    if not old.empty:
        by_ticker = old.set_index('ticker')
        for idx, row in current.iterrows():
            t = row['ticker']
            if t in by_ticker.index:
                for field in ['instrument_id', 'first_seen', 'sector', 'industry']:
                    current.at[idx, field] = by_ticker.loc[t, field]
        # Do not deactivate on one missing snapshot; flag for review.
        missing = old[~old.ticker.isin(current.ticker)].copy()
        missing['is_active'] = False  # unconfirmed: never delete historical data
        current = pd.concat([current, missing], ignore_index=True)
    write_parquet(current, path)
    return current[current.is_active]


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
        active = update_universe(universe)
        limit = int(cfg.get('max_tickers', 0))
        if limit > 0:
            active = active.head(limit)
        log = []
        for _, item in active.iterrows():
            ticker = item['ticker']
            base = BASE.format(symbol_slug(ticker))
            if cfg.get('collect_stockanalysis', True):
              try:
                profile_html = fetch(session, base, cfg['request_delay_seconds'], cfg['timeout_seconds'])
                profile = parse_profile(profile_html)
                instruments = load_existing(DATA / 'dimensions/instruments.parquet')
                mask = instruments.ticker == ticker
                for key in ['sector', 'industry']:
                    if profile[key]:
                        instruments.loc[mask, key] = profile[key]
                write_parquet(instruments, DATA / 'dimensions/instruments.parquet')
              except requests.RequestException as exc:
                log.append({'ticker': ticker, 'page': 'profile', 'status': 'error', 'detail': str(exc)[:300], 'at': utc_now()})
            if cfg.get('collect_finviz', False):
                from urllib.parse import quote
                finviz_url = 'https://finviz.com/quote.ashx?t=' + quote(ticker, safe='')
                try:
                    html = fetch(session, finviz_url, cfg['request_delay_seconds'], cfg['timeout_seconds'])
                    now = utc_now()
                    rows = parse_finviz_snapshot(html, ticker, now)
                    if not rows:
                        raise ValueError('FINVIZ returned zero snapshot metrics')
                    count = merge_records(DATA / 'finviz' / 'snapshots.parquet', rows,
                                          ['ticker', 'metric'], keep_revisions=True)
                    profile = parse_finviz_profile(html)
                    instruments = load_existing(DATA / 'dimensions/instruments.parquet')
                    if not instruments.empty and 'ticker' in instruments:
                        mask = instruments.ticker == ticker
                        for key in ('sector', 'industry'):
                            if profile[key] and key in instruments:
                                instruments.loc[mask, key] = profile[key]
                        write_parquet(instruments, DATA / 'dimensions/instruments.parquet')
                    log.append({'ticker': ticker, 'page': 'finviz', 'status': 'ok',
                                'detail': str(count), 'at': now})
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
        if errors:
            raise SystemExit(1)
    finally:
        session.close()

if __name__ == '__main__':
    main()
