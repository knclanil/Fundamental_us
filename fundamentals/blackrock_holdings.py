"""BlackRock iShares ETF holdings ingestion (v4.3.2.13).

Only EQUITY rows are constituents. Market Value is ETF position value, NOT issuer
market capitalization. This module never labels holdings as $10B+ companies.
"""
import csv
import io
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE = 'https://www.blackrock.com/varnish-api/blk-one01-product-data/product-data/api/v1/get-fund-document'
FUNDS = {'IWB': '239707', 'IWM': '239710', 'IWV': '239714'}
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; MaketData/4.3.2.13)', 'Accept': 'text/csv,application/octet-stream,*/*'}
FIELDS = ['ticker','company_name','sector','location','exchange','in_IWB','in_IWM','in_IWV','etf_count','holdings_as_of']


def parse_holdings(raw, fund):
    """Parse actual BlackRock CSV preamble, detect header and holdings date."""
    if fund not in FUNDS:
        raise ValueError(f'Unknown fund: {fund}')
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8-sig')
    rows = list(csv.reader(io.StringIO(raw.lstrip('\ufeff'))))
    header = next((i for i, row in enumerate(rows) if len(row) > 4 and row[:2] == ['Ticker', 'Name'] and 'Asset Class' in row), None)
    if header is None:
        raise ValueError(f'{fund}: BlackRock holdings header missing')
    observed = next((r[1] for r in rows[:header] if len(r) >= 2 and r[0].strip() == 'Fund Holdings as of'), None)
    if not observed:
        raise ValueError(f'{fund}: holdings as-of date missing')
    as_of = datetime.strptime(observed.strip(), '%b %d, %Y').date().isoformat()
    indices = {name: i for i, name in enumerate(rows[header])}
    required = {'Ticker', 'Name', 'Sector', 'Asset Class', 'Location', 'Exchange'}
    if not required.issubset(indices):
        raise ValueError(f'{fund}: missing required columns')
    out = {}
    for row in rows[header+1:]:
        if len(row) <= max(indices.values()):
            continue
        if row[indices['Asset Class']].strip().upper() != 'EQUITY':
            continue
        ticker = row[indices['Ticker']].strip().upper().replace('.', '-')
        if not re.fullmatch(r'[A-Z][A-Z0-9-]{0,14}', ticker):
            continue
        if ticker in out:
            continue  # duplicate positions for the same ticker
        out[ticker] = {'ticker': ticker, 'company_name': row[indices['Name']].strip(),
                       'sector': row[indices['Sector']].strip(),
                       'location': row[indices['Location']].strip(),
                       'exchange': row[indices['Exchange']].strip(),
                       'holdings_as_of': as_of}
    if len(out) < 100:
        raise ValueError(f'{fund}: suspiciously small holdings dataset ({len(out)})')
    return out


def combine(fund_rows):
    combined = {}
    for fund in FUNDS:
        if fund not in fund_rows or not fund_rows[fund]:
            raise ValueError(f'Missing validated {fund} holdings')
        for ticker, row in fund_rows[fund].items():
            if ticker not in combined:
                combined[ticker] = {**row, **{f'in_{f}': 0 for f in FUNDS}}
            combined[ticker][f'in_{fund}'] = 1
    for row in combined.values():
        row['etf_count'] = sum(row[f'in_{f}'] for f in FUNDS)
    return [combined[t] for t in sorted(combined)]


def fetch(fund, as_of, session=None):
    if fund not in FUNDS:
        raise ValueError(f'Unknown fund {fund}')
    if not re.fullmatch(r'\d{8}', as_of):
        raise ValueError('as_of must be YYYYMMDD')
    session = session or requests.Session()
    response = session.get(BASE, params={
        'appType': 'PRODUCT_PAGE', 'appSubType': 'ISHARES', 'targetSite': 'us-ishares',
        'locale': 'en_US', 'portfolioId': FUNDS[fund], 'userType': 'individual',
        'asOfDate': as_of, 'component': 'holdings'}, headers=HEADERS, timeout=60)
    response.raise_for_status()
    parsed = parse_holdings(response.content, fund)
    requested = datetime.strptime(as_of, '%Y%m%d').date().isoformat()
    actual = next(iter(parsed.values()))['holdings_as_of']
    if actual != requested:
        raise ValueError(f'{fund}: requested {requested} but provider returned {actual}')
    return parsed


def write_combined(rows, destination):
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({k: row.get(k, '') for k in FIELDS} for row in rows)
    temporary.replace(path)
    return path


def read_combined(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        if not reader.fieldnames or not set(FIELDS).issubset(reader.fieldnames):
            raise ValueError('Invalid combined BlackRock holdings CSV')
        rows = list(reader)
    if len(rows) < 100:
        raise ValueError('Combined holdings file unexpectedly small')
    return rows


def collect(as_of, output, snapshot_dir=None, offline=False):
    funds = {}
    for fund in FUNDS:
        if offline:
            if not snapshot_dir:
                raise ValueError('Offline mode requires snapshot_dir')
            content = (Path(snapshot_dir) / f'{fund}_holdings.csv').read_bytes()
            funds[fund] = parse_holdings(content, fund)
        else:
            funds[fund] = fetch(fund, as_of)
        print(f'{fund} equities={len(funds[fund])} date={next(iter(funds[fund].values()))["holdings_as_of"]}', flush=True)
    dates = {row['holdings_as_of'] for data in funds.values() for row in data.values()}
    if len(dates) != 1:
        raise ValueError(f'ETF snapshots have mismatched dates: {dates}')
    if next(iter(dates)) != datetime.strptime(as_of, '%Y%m%d').date().isoformat():
        raise ValueError('Holdings date differs from requested date')
    rows = combine(funds)
    write_combined(rows, output)
    print(f'COMBINED unique_tickers={len(rows)} output={output}', flush=True)
    return rows


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--as-of', help='YYYYMMDD exact holdings date')
    p.add_argument('--latest', action='store_true', help='Try recent business dates, newest first')
    p.add_argument('--output', default='data/blackrock_holdings_latest.csv')
    p.add_argument('--offline-snapshots', default=None, help='Directory containing three uploaded original CSVs')
    a = p.parse_args()
    if a.latest and a.as_of:
        p.error('Choose --latest or --as-of')
    if a.latest:
        today = datetime.now(timezone.utc).date()
        errors = []
        for days_back in range(1, 15):
            day = today - timedelta(days=days_back)
            if day.weekday() >= 5:
                continue
            try:
                collect(day.strftime('%Y%m%d'), a.output)
                return
            except (requests.RequestException, ValueError, UnicodeError) as exc:
                errors.append(f'{day}: {type(exc).__name__}: {exc}')
        raise RuntimeError('No validated recent BlackRock holdings; previous snapshot preserved. ' + '; '.join(errors))
    if not a.as_of:
        p.error('Choose --as-of or --latest')
    collect(a.as_of, a.output, a.offline_snapshots, bool(a.offline_snapshots))

if __name__ == '__main__':
    main()
