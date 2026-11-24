"""v3.2.0 (2026-11-24): market-cap ranking and incremental selection.
Market cap is sourced from previously stored FINVIZ snapshots or an optional
licensed CSV; unknown companies are not guessed to be large-cap.
"""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pandas as pd

CAP_GROUPS = [('mega_cap', 200e9), ('large_cap', 10e9), ('mid_cap', 2e9),
              ('small_cap', 300e6), ('micro_cap', 50e6), ('nano_cap', 0)]
ORDER = {name: i for i, (name, _) in enumerate(CAP_GROUPS)}
ORDER['unknown'] = len(ORDER)

def parse_cap(raw):
    if raw is None or pd.isna(raw):
        return None
    s = str(raw).strip().upper().replace(',', '').replace('$', '')
    m = re.fullmatch(r'([+-]?\d+(?:\.\d+)?)\s*([KMBT]?)', s)
    if not m:
        return None
    n = float(m.group(1)) * {'':1, 'K':1e3, 'M':1e6, 'B':1e9, 'T':1e12}[m.group(2)]
    return n if n >= 0 else None

def cap_group(cap):
    if cap is None or pd.isna(cap):
        return 'unknown'
    for name, threshold in CAP_GROUPS:
        if cap >= threshold:
            return name
    return 'unknown'

def cap_lookup(snapshot_path, seed_path=None, alpha_cache_path=None):
    caps = {}
    if snapshot_path.exists():
        s = pd.read_parquet(snapshot_path)
        if {'ticker','metric','raw_value'}.issubset(s.columns):
            s = s[s.metric.astype(str).str.lower().eq('market cap')].copy()
            if 'observed_at' in s:
                s = s.sort_values('observed_at')
            for _, r in s.iterrows():
                v = parse_cap(r.raw_value)
                if v is not None:
                    caps[str(r.ticker).upper()] = v
    if seed_path and Path(seed_path).exists():
        df = pd.read_csv(seed_path)
        if not {'ticker','market_cap_usd'}.issubset(df.columns):
            raise ValueError('Market-cap seed must have ticker,market_cap_usd columns')
        # Seed takes precedence; only supply an authorized, dated market-cap feed.
        for _, r in df.iterrows():
            v = parse_cap(r.market_cap_usd)
            if v is not None:
                caps[str(r.ticker).upper()] = v
    if alpha_cache_path and Path(alpha_cache_path).exists():
        cached = json.loads(Path(alpha_cache_path).read_text())
        for ticker, item in cached.items():
            value = parse_cap(item.get('market_cap_usd')) if isinstance(item, dict) else None
            if value is not None:
                caps[ticker.upper()] = value
    return caps

def latest_successes(snapshot_path):
    if not snapshot_path.exists():
        return {}
    df = pd.read_parquet(snapshot_path)
    if not {'ticker','observed_at','metric'}.issubset(df.columns):
        return {}
    df = df[df.metric.astype(str).eq('Price')]
    dates = pd.to_datetime(df.observed_at, utc=True, errors='coerce')
    df = df.assign(_date=dates).dropna(subset=['_date'])
    return df.groupby('ticker')['_date'].max().to_dict()

def select_batch(universe, snapshot_path, seed_path, batch_size, refresh_hours=24, retry_path=None, now=None, alpha_cache_path=None):
    now = now or datetime.now(timezone.utc)
    caps = cap_lookup(snapshot_path, seed_path, alpha_cache_path)
    success = latest_successes(snapshot_path)
    retry = {}
    if retry_path and Path(retry_path).exists():
        retry = json.loads(Path(retry_path).read_text())
    pending = []
    for _, row in universe.iterrows():
        t = str(row.ticker).upper()
        last = success.get(t)
        # Exclude recently collected; never assume an uncollected ticker's cap.
        if last is not None and now - last.to_pydatetime() < timedelta(hours=refresh_hours):
            continue
        cap = caps.get(t)
        group = cap_group(cap)
        failed = any(key.startswith(t + '|') for key in retry)
        pending.append((ORDER[group], -(cap or 0), 0 if last is None else 1,
                        0 if failed else 1, t))
    # First prioritize known mega/large/mid; within tier prefer never collected.
    # Unknown cap is last; it needs an authorized market-cap feed for true priority.
    pending.sort(key=lambda x: (x[0], x[2], x[3], x[1], x[4]))
    selected = [x[4] for x in pending[:batch_size]]
    indexed = universe.set_index('ticker')
    return indexed.loc[selected].reset_index(), {'eligible': len(pending),
        'known_caps': sum(t in caps for t in universe.ticker),
        'selected': len(selected), 'unknown_caps': sum(t not in caps for t in universe.ticker)}
