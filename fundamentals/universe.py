"""S&P 500 constituent universe; NOT a verified $10B market-cap screen.

Version 4.1.1: live Wikipedia table, with an explicitly small checked-in
bootstrap list if the live provider is unavailable. Never label bootstrap as
full S&P 500 coverage. Does not depend on Nasdaq screener.
"""
import csv
import io
import re
from pathlib import Path
import requests
from bs4 import BeautifulSoup

WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
BOOTSTRAP = Path(__file__).resolve().parent.parent / "data" / "sp500_bootstrap.csv"

def parse_cap(value):
    if isinstance(value, (int, float)): return float(value)
    if not value: return None
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*([KMBT]?)", str(value).strip().replace(",", "").replace("$", ""), re.I)
    if not match: return None
    return float(match.group(1)) * {"":1,"K":1e3,"M":1e6,"B":1e9,"T":1e12}[match.group(2).upper()]

def parse_wikipedia(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="constituents")
    if table is None: raise ValueError("S&P 500 constituents table not found")
    rows=[]; seen=set()
    for tr in table.select("tbody tr"):
        cells=tr.find_all("td")
        if len(cells)<2: continue
        ticker=cells[0].get_text(" ", strip=True).replace(".", "-").upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9-]*",ticker) or ticker in seen: continue
        seen.add(ticker)
        rows.append({"ticker":ticker,"name":cells[1].get_text(" ",strip=True),"universe_source":"sp500_wikipedia","market_cap":None})
    if not 450 <= len(rows) <= 550:
        raise ValueError(f"Unexpected S&P 500 universe size: {len(rows)}")
    return rows

def fetch_large_caps(min_cap=10_000_000_000, session=None, fallback_path=BOOTSTRAP):
    # Backward-compatible signature. min_cap is deliberately NOT applied:
    # S&P 500 membership is a proxy, not proof of a market cap threshold.
    session = session or requests.Session()
    try:
        response=session.get(WIKI,timeout=25,headers={"User-Agent":"MaketData/4.1.1 (educational research)","Accept":"text/html"})
        response.raise_for_status()
        rows=parse_wikipedia(response.text)
        print(f"UNIVERSE source=Wikipedia S&P500 count={len(rows)} (not market-cap filtered)",flush=True)
        return rows
    except (requests.RequestException, ValueError) as exc:
        if not fallback_path.exists(): raise RuntimeError(f"Universe unavailable and no fallback: {exc}") from exc
        with fallback_path.open(newline="",encoding="utf-8") as f:
            rows=[{"ticker":r["ticker"],"name":r["name"],"universe_source":"bootstrap_partial","market_cap":None} for r in csv.DictReader(f)]
        if not rows: raise RuntimeError("Bootstrap universe empty") from exc
        print(f"WARNING: Live S&P 500 universe unavailable ({type(exc).__name__}). Using PARTIAL bootstrap of {len(rows)} tickers; NOT complete coverage.",flush=True)
        return rows

def join_sec(universe, sec_rows):
    mapping={str(r['ticker']).upper().replace('.','-'):r for r in sec_rows}
    joined=[]; seen=set()
    for row in universe:
        ticker=row['ticker'].upper().replace('.','-')
        sec=mapping.get(ticker)
        if sec and int(sec['cik_str']) not in seen:
            seen.add(int(sec['cik_str']))
            joined.append({**row,'ticker':ticker,'cik':int(sec['cik_str']),'sec_name':sec['title']})
    if not joined: raise RuntimeError('No tickers matched SEC CIK list')
    return joined


US_EXCHANGES = {"NASDAQ", "NYSE", "NYSE AMERICAN", "NYSEAMERICAN", "NYSE ARCA", "NYSEARCA", "AMEX"}

def load_us_large_cap(csv_path, official, min_cap=10_000_000_000):
    """Select verified U.S.-listed $10B+ issuers from an externally sourced CSV.

    The SEC ticker feed has no market cap. Fail closed rather than silently
    treating SEC-listed or S&P 500 membership as a cap screen.
    Required columns: ticker,market_cap_usd,exchange,as_of,source.
    """
    from datetime import date
    from .cik_sync import normalize_ticker
    if not csv_path:
        raise ValueError('us_large_cap requires --universe-file with market-cap observations')
    path = Path(csv_path)
    if not path.is_file():
        raise ValueError(f'Market-cap CSV not found: {path}')
    rows = {}
    with path.open(newline='', encoding='utf-8-sig') as handle:
        reader = csv.DictReader(handle)
        required = {'ticker', 'market_cap_usd', 'exchange', 'as_of', 'source'}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError(f'Market-cap CSV requires columns: {sorted(required)}')
        for line, row in enumerate(reader, start=2):
            ticker = normalize_ticker(row['ticker'])
            exchange = (row['exchange'] or '').strip().upper().replace('_', ' ')
            if exchange not in US_EXCHANGES:
                continue
            try:
                cap = float((row['market_cap_usd'] or '').replace(',', '').replace('$', ''))
                observed = date.fromisoformat((row['as_of'] or '').strip())
            except (ValueError, TypeError) as exc:
                raise ValueError(f'Invalid market cap/date at CSV line {line}') from exc
            if not (0 < cap < float('inf')) or observed > date.today():
                raise ValueError(f'Invalid market cap or future date at CSV line {line}')
            if not (row['source'] or '').strip():
                raise ValueError(f'Missing market cap source at CSV line {line}')
            if cap < min_cap or ticker not in official:
                continue
            item = {'ticker': ticker, 'name': official[ticker]['sec_name'],
                    'universe_source': 'us_large_cap_market_cap_csv', 'market_cap': cap,
                    'market_cap_usd': cap, 'market_cap_as_of': observed.isoformat(),
                    'market_cap_source': row['source'].strip(), 'exchange': exchange}
            previous = rows.get(ticker)
            if previous is None or item['market_cap_as_of'] > previous['market_cap_as_of']:
                rows[ticker] = item
    if not rows:
        raise ValueError('No eligible SEC-mapped U.S.-listed companies >= threshold; no collection performed')
    return [rows[t] for t in sorted(rows)]

def select_universe(mode, official, tickers=None, csv_path=None, min_cap=None):
    """Resolve the *requested* universe, never infer cap tiers from SEC tickers.

    Modes: sp500 (membership), sec_all (SEC ticker feed, not all US issuers),
    custom (explicit symbols from CSV), tickers (explicit symbols from CLI).
    """
    from .cik_sync import normalize_ticker
    if mode == 'blackrock_holdings':
        from .blackrock_holdings import read_combined
        if not csv_path:
            raise ValueError('blackrock_holdings requires --universe-file')
        holdings = read_combined(csv_path)
        return [{'ticker': normalize_ticker(r['ticker']), 'name': r['company_name'],
                 'universe_source': 'blackrock_etf_holdings_not_market_cap_verified',
                 'market_cap': None, 'holdings_as_of': r['holdings_as_of'],
                 'in_IWB': int(r['in_IWB']), 'in_IWM': int(r['in_IWM']),
                 'in_IWV': int(r['in_IWV'])} for r in holdings
                if normalize_ticker(r['ticker']) in official]
    if mode == 'us_large_cap':
        return load_us_large_cap(csv_path, official, min_cap or 10_000_000_000)
    if mode == 'sp500':
        return fetch_large_caps(min_cap or 10_000_000_000)
    if mode == 'sec_all':
        return [{'ticker': t, 'name': row['sec_name'], 'universe_source': 'sec_ticker_feed_not_market_cap', 'market_cap': None}
                for t, row in sorted(official.items())]
    if mode == 'custom':
        if not csv_path: raise ValueError('custom universe requires --universe-file')
        path = Path(csv_path)
        if not path.is_file(): raise ValueError(f'Universe file not found: {path}')
        with path.open(newline='', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames or 'ticker' not in reader.fieldnames:
                raise ValueError('Universe CSV requires a ticker column')
            symbols = [normalize_ticker(row['ticker']) for row in reader]
    elif mode == 'tickers':
        symbols = [normalize_ticker(t) for t in (tickers or [])]
    else:
        raise ValueError(f'Unsupported universe: {mode}')
    symbols = list(dict.fromkeys(t for t in symbols if t))
    if not symbols: raise ValueError('Universe has no tickers')
    return [{'ticker': t, 'name': official.get(t, {}).get('sec_name', t),
             'universe_source': 'custom_csv' if mode == 'custom' else 'explicit_tickers',
             'market_cap': None} for t in symbols]
