import csv
import tempfile
import unittest
from pathlib import Path
from fundamentals.universe import load_us_large_cap

OFFICIAL = {'AAA': {'sec_name': 'AAA Corp'}, 'BBB': {'sec_name': 'BBB Corp'}, 'CCC': {'sec_name': 'CCC Corp'}}

class LargeCapTests(unittest.TestCase):
    def make_csv(self, rows):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / 'caps.csv'
        with path.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['ticker','market_cap_usd','exchange','as_of','source'])
            writer.writeheader()
            writer.writerows(rows)
        return str(path)

    def test_threshold_exchange_and_sec_identity(self):
        path = self.make_csv([
            dict(ticker='AAA', market_cap_usd='12000000000', exchange='NASDAQ', as_of='2026-11-20', source='provider'),
            dict(ticker='BBB', market_cap_usd='9000000000', exchange='NYSE', as_of='2026-11-20', source='provider'),
            dict(ticker='CCC', market_cap_usd='20000000000', exchange='LSE', as_of='2026-11-20', source='provider'),
            dict(ticker='ZZZ', market_cap_usd='30000000000', exchange='NASDAQ', as_of='2026-11-20', source='provider'),
        ])
        result = load_us_large_cap(path, OFFICIAL)
        self.assertEqual([r['ticker'] for r in result], ['AAA'])
        self.assertEqual(result[0]['market_cap_source'], 'provider')

    def test_latest_duplicate_wins(self):
        path = self.make_csv([
            dict(ticker='AAA', market_cap_usd='12000000000', exchange='NASDAQ', as_of='2026-11-19', source='old'),
            dict(ticker='AAA', market_cap_usd='13000000000', exchange='NASDAQ', as_of='2026-11-20', source='new'),
        ])
        self.assertEqual(load_us_large_cap(path, OFFICIAL)[0]['market_cap'], 13_000_000_000)

    def test_missing_file_fails_closed(self):
        with self.assertRaises(ValueError):
            load_us_large_cap(None, OFFICIAL)

    def test_invalid_market_cap_fails_closed(self):
        path = self.make_csv([dict(ticker='AAA', market_cap_usd='not-a-number', exchange='NYSE', as_of='2026-11-20', source='provider')])
        with self.assertRaises(ValueError):
            load_us_large_cap(path, OFFICIAL)

if __name__ == '__main__':
    unittest.main()
