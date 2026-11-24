"""v3.1.3 fund detection regression tests."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from finviz import is_fund_snapshot, parse_finviz_snapshot


def html_with_labels(labels):
    rows = ''.join(f'<tr><td>{label}</td><td>123</td></tr>' for label in labels)
    return f'<table class="snapshot-table2">{rows}</table>'


def test_fund_detected_from_actual_grn_style_labels():
    assert is_fund_snapshot(html_with_labels(['AUM', 'Expense', 'ETF Type', 'Asset Type', 'Price']))


def test_common_stock_not_detected():
    assert not is_fund_snapshot(html_with_labels(['P/E', 'Market Cap', 'Price', 'Volume', 'RSI (14)']))


def test_single_fund_marker_not_enough():
    assert not is_fund_snapshot(html_with_labels(['AUM', 'Price', 'Market Cap']))
