"""FINVIZ overview snapshot parser v3.0.0 (2026-11-23).
Changelog: initial independent parser for paired label/value cells; raw values preserved.
Only use with authorized access. This parser is not validated against live FINVIZ HTML.
"""
import re
from bs4 import BeautifulSoup

MISSING = {'', '-', '--', '—', 'N/A'}

def parse_finviz_snapshot(html, ticker, observed_at):
    """Extract all label/value pairs from the FINVIZ snapshot table.

    FINVIZ currently commonly uses table.snapshot-table2. This is a
    best-effort parser; fail closed if the structure is unrecognized.
    """
    soup = BeautifulSoup(html, 'lxml')
    table = soup.select_one('table.snapshot-table2')
    if table is None:
        raise ValueError('FINVIZ snapshot table not found (page or access may have changed)')
    out = []
    for tr in table.select('tr'):
        cells = tr.find_all(['td', 'th'], recursive=False)
        if len(cells) % 2:
            raise ValueError('Unexpected odd number of FINVIZ snapshot cells')
        for i in range(0, len(cells), 2):
            label = cells[i].get_text(' ', strip=True)
            value = cells[i + 1].get_text(' ', strip=True)
            if not label:
                continue
            out.append({'ticker': ticker, 'metric': label, 'raw_value': value,
                        'observed_at': observed_at, 'source_page': 'finviz_overview'})
    if len(out) < 20:
        raise ValueError(f'Only {len(out)} FINVIZ metrics found; page may be incomplete')
    return out

def parse_finviz_profile(html):
    """Extract sector/industry from profile links, without inventing missing values."""
    soup = BeautifulSoup(html, 'lxml')
    result = {'sector': None, 'industry': None}
    for link in soup.select('a[href]'):
        href = link.get('href', '')
        if 'sec=' in href and result['sector'] is None:
            result['sector'] = link.get_text(' ', strip=True) or None
        if 'ind=' in href and result['industry'] is None:
            result['industry'] = link.get_text(' ', strip=True) or None
    return result
