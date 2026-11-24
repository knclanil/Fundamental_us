from datetime import datetime, timezone
import json
import pandas as pd
from src.priority import select_batch, parse_cap

def test_zero_cap_unknown():
    assert parse_cap('0') is None
    assert parse_cap('15B') == 15e9

def test_404_cooldown_and_large_first(tmp_path):
    universe = pd.DataFrame({'ticker':['BAD','BIG','MID','SMALL']})
    seed = tmp_path/'caps.csv'
    seed.write_text('ticker,market_cap_usd\nBAD,500000000000\nBIG,150000000000\nMID,5000000000\nSMALL,200000000\n')
    skip = tmp_path/'skips.json'
    skip.write_text(json.dumps({'BAD':{'last_skipped_at':'2026-11-24T00:00:00+00:00'}}))
    selected, diagnostics = select_batch(universe,tmp_path/'missing.parquet',seed,3,now=datetime(2026,11,24,12,tzinfo=timezone.utc),skip_path=skip)
    assert selected.ticker.tolist()==['BIG','MID','SMALL']
    assert diagnostics['skipped_cooldown']==1
