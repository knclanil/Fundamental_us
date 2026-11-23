from src.pipeline import parse_statistics, parse_financials, symbol_slug, parse_exchange

def test_slug():
    assert symbol_slug('BRK.B') == 'brk-b'

def test_stats():
    html = '<h2>Valuation</h2><table><tr><td>PE Ratio</td><td>12.5</td></tr></table>'
    rows = parse_statistics(html, 'MU', 'now')
    assert rows[0]['metric'] == 'PE Ratio'
    assert rows[0]['category'] == 'Valuation'

def test_financials():
    html = '<table><tr><th>Metric</th><th>2025</th><th>2024</th></tr><tr><td>Revenue</td><td>100</td><td>80</td></tr></table>'
    rows = parse_financials(html, 'MU', 'income', 'now')
    assert len(rows) == 2
    assert rows[0]['period_label'] == '2025'

def test_exchange():
    text = 'Symbol|Security Name|ETF|Test Issue\nMU|Micron Technology|N|N\nABC|Sample ETF|Y|N\nFile Creation Time: 2026\n'
    df = parse_exchange(text, 'Symbol')
    assert df.ticker.tolist() == ['MU']
