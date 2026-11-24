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
