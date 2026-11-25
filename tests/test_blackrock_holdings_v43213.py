import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from fundamentals.blackrock_holdings import parse_holdings, combine, read_combined, write_combined

ROOT = Path(__file__).resolve().parent.parent

class BlackRockHoldingsTests(unittest.TestCase):
    def test_actual_uploaded_snapshots(self):
        funds = {f: parse_holdings((ROOT/'data'/f'{f}_holdings.csv').read_bytes(), f)
                 for f in ('IWB', 'IWM', 'IWV')}
        self.assertGreater(len(funds['IWB']), 900)
        self.assertGreater(len(funds['IWM']), 1800)
        self.assertGreater(len(funds['IWV']), 2400)
        rows = combine(funds)
        self.assertGreater(len(rows), 2800)
        self.assertEqual(len(rows), len({r['ticker'] for r in rows}))
        self.assertEqual({r['holdings_as_of'] for r in rows}, {'2026-11-24'})
        with TemporaryDirectory() as directory:
            output = Path(directory)/'holdings.csv'
            write_combined(rows, output)
            self.assertEqual(len(read_combined(output)), len(rows))

    def test_reject_invalid_response(self):
        with self.assertRaises(ValueError):
            parse_holdings('<html>blocked</html>', 'IWB')

if __name__ == '__main__':
    unittest.main()
