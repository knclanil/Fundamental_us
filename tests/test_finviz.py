"""v3.0.0 FINVIZ parser tests with synthetic HTML fixtures."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from finviz import parse_finviz_snapshot, parse_finviz_profile

def test_snapshot_pairs():
    cells = ''.join(f'<td>Metric {i}</td><td>{i}%</td>' for i in range(24))
    rows = parse_finviz_snapshot(f'<table class="snapshot-table2"><tr>{cells}</tr></table>', 'GOOGL', '2026-11-23')
    assert len(rows) == 24
    assert rows[0]['raw_value'] == '0%'
    assert rows[-1]['metric'] == 'Metric 23'

def test_missing_snapshot_fails():
    with pytest.raises(ValueError, match='not found'):
        parse_finviz_snapshot('<html></html>', 'MU', 'now')

def test_profile():
    html = '<a href="screener.ashx?v=111&f=sec_technology">Technology</a><a href="screener.ashx?v=111&f=ind_semiconductors">Semiconductors</a>'
    # No query parameters sec=/ind= in this synthetic page: fail safe.
    assert parse_finviz_profile(html) == {'sector': None, 'industry': None}
