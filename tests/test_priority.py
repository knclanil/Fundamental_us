"""v3.2.0 - market cap classification and incremental selection."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import pandas as pd
from priority import parse_cap, cap_group, select_batch

def test_cap():
    assert parse_cap('3.2T') == 3.2e12
    assert parse_cap('5B') == 5e9
    assert parse_cap('-') is None
    assert cap_group(11e9) == 'large_cap'
    assert cap_group(3e9) == 'mid_cap'

def test_seed_priority(tmp_path):
    seed = tmp_path / 'caps.csv'
    seed.write_text('ticker,market_cap_usd\nA,1000000000\nB,200000000000\nC,4000000000\n')
    universe = pd.DataFrame({'ticker':['A','B','C','D']})
    selected, info = select_batch(universe, tmp_path / 'missing.parquet', seed, 3)
    assert selected.ticker.tolist() == ['B','C','A']
    assert info['unknown_caps'] == 1
