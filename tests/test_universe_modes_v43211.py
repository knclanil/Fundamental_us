"""Version 4.3.2.11: explicit universe selection, no implicit cap claims."""
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fundamentals.universe import select_universe

OFFICIAL = {'AAPL': {'sec_name': 'Apple'}, 'XYZ': {'sec_name': 'Example'}, 'BRK-B': {'sec_name': 'Berkshire'}}

class UniverseModeTests(unittest.TestCase):
    def test_explicit_tickers(self):
        rows = select_universe('tickers', OFFICIAL, tickers=['aapl', 'AAPL', 'BRK.B'])
        self.assertEqual([r['ticker'] for r in rows], ['AAPL', 'BRK-B'])
    def test_sec_all_is_not_cap_classification(self):
        rows = select_universe('sec_all', OFFICIAL)
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r['market_cap'] is None for r in rows))
    def test_custom_csv(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'list.csv'
            path.write_text('ticker\nXYZ\nAAPL\nXYZ\n', encoding='utf-8')
            self.assertEqual([r['ticker'] for r in select_universe('custom', OFFICIAL, csv_path=path)], ['XYZ', 'AAPL'])
    def test_missing_csv_rejected(self):
        with self.assertRaises(ValueError): select_universe('custom', OFFICIAL)
    def test_sp500_preserves_existing_source(self):
        with patch('fundamentals.universe.fetch_large_caps', return_value=[{'ticker':'AAPL'}]) as mocked:
            self.assertEqual(select_universe('sp500', OFFICIAL), [{'ticker':'AAPL'}])
            mocked.assert_called_once()
    def test_bad_mode_rejected(self):
        with self.assertRaises(ValueError): select_universe('smallcap', OFFICIAL)

if __name__ == '__main__': unittest.main()
