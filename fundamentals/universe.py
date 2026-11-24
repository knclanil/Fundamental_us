"""NASDAQ screener is a free best-effort market-cap feed, not an SLA-backed API."""
import re
import requests

ENDPOINT='https://api.nasdaq.com/api/screener/stocks'
EXCHANGES=('nasdaq','nyse','amex')

def parse_cap(value):
    if isinstance(value,(int,float)): return float(value)
    if not value: return None
    s=str(value).strip().replace(',','').replace('$','')
    match=re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)\s*([KMBT]?)',s,re.I)
    if not match: return None
    return float(match.group(1))*{'':1,'K':1e3,'M':1e6,'B':1e9,'T':1e12}[match.group(2).upper()]

def fetch_large_caps(min_cap=10_000_000_000,session=None):
    session=session or requests.Session()
    session.headers.update({'User-Agent':'Mozilla/5.0 (compatible; MaketData research)','Accept':'application/json','Origin':'https://www.nasdaq.com','Referer':'https://www.nasdaq.com/'})
    found={}
    for exchange in EXCHANGES:
        response=session.get(ENDPOINT,params={'tableonly':'true','limit':'10000','offset':'0','exchange':exchange,'download':'true'},timeout=45)
        response.raise_for_status()
        data=response.json().get('data') or {}
        table=data.get('table') or {}
        rows=table.get('rows')
        if not isinstance(rows,list): raise RuntimeError(f'Unexpected Nasdaq response for {exchange}; refusing incomplete universe')
        total=table.get('totalRecords')
        if total is not None and int(total)>len(rows): raise RuntimeError(f'Nasdaq response truncated for {exchange}')
        for row in rows:
            ticker=str(row.get('symbol') or '').strip().upper()
            cap=parse_cap(row.get('marketCap'))
            if ticker and cap is not None and cap>=min_cap and re.fullmatch(r'[A-Z][A-Z0-9.\-]*',ticker):
                found[ticker]={'ticker':ticker,'market_cap':cap,'exchange':exchange,'name':row.get('name','')}
    if not found: raise RuntimeError('No large caps found; check universe provider')
    return sorted(found.values(),key=lambda r:(-r['market_cap'],r['ticker']))

def join_sec(universe,sec_rows):
    mapping={str(r['ticker']).upper():r for r in sec_rows}
    joined=[]
    for row in universe:
        ticker=row['ticker']; sec=mapping.get(ticker) or mapping.get(ticker.replace('.','-')) or mapping.get(ticker.replace('-','.'))
        if sec:
            joined.append({**row,'cik':int(sec['cik_str']),'sec_name':sec['title']})
    return joined
