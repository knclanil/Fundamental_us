"""FINVIZ parser regression tests v3.0.4 (2026-11-23)."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from finviz import parse_finviz_snapshot, parse_finviz_profile


def snapshot_html(n=72):
    labels = ['Market Cap', 'P/E', 'Price', 'Volume', 'RSI (14)'] + [f'Metric {i}' for i in range(n-5)]
    rows = []
    for i in range(0, len(labels), 6):
        cells = ''.join(f'<td class="snapshot-td2-cp">{label}</td><td class="snapshot-td2">{j}%</td>'
                        for j, label in enumerate(labels[i:i+6], i))
        rows.append(f'<tr>{cells}</tr>')
    return '<table class="snapshot-table2">' + ''.join(rows) + '</table>'


def test_complete_screenshot_style_table():
    rows = parse_finviz_snapshot(snapshot_html(), 'GOOG', '2026-11-23')
    assert len(rows) == 72
    assert {r['metric'] for r in rows} >= {'Market Cap', 'P/E', 'Price', 'Volume', 'RSI (14)'}
    assert rows[0]['raw_value'] == '0%'


def test_partial_table_rejected():
    with pytest.raises(ValueError, match='Incomplete FINVIZ snapshot'):
        parse_finviz_snapshot(snapshot_html(14), 'MU', 'now')


def test_missing_snapshot_fails():
    with pytest.raises(ValueError, match='not found'):
        parse_finviz_snapshot('<html></html>', 'MU', 'now')


def test_preserves_missing_and_compound_values():
    html = snapshot_html().replace('>0%</td>', '>--</td>').replace('>1%</td>', '>33.35% 29.82%</td>')
    rows = parse_finviz_snapshot(html, 'GOOG', 'now')
    assert rows[0]['raw_value'] == '--'
    assert rows[1]['raw_value'] == '33.35% 29.82%'


def test_profile():
    html = '<a href="screener.ashx?v=111&f=sec_technology">Technology</a><a href="screener.ashx?v=111&f=ind_semiconductors">Semiconductors</a>'
    assert parse_finviz_profile(html) == {'sector': 'Technology', 'industry': 'Semiconductors'}
