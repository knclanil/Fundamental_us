import unittest
from fundamentals.cik_sync import normalize_ticker, cik10, issuer_guard
class TestCikSync(unittest.TestCase):
    def test_share_classes(self):
        self.assertEqual(normalize_ticker(' brk.b '), 'BRK-B')
        self.assertEqual(normalize_ticker('bf.b'), 'BF-B')
    def test_padding(self):
        self.assertEqual(cik10(34088), '0000034088')
    def test_reject_bad(self):
        with self.assertRaises(ValueError): cik10('ABC')
    def test_xom_guard(self):
        self.assertIsNotNone(issuer_guard('XOM', {'cik':'0002115436','sec_name':'ExxonMobil Holdings Corporation'}))
        self.assertIsNone(issuer_guard('XOM', {'cik':'0000034088','sec_name':'Exxon Mobil Corporation'}))
if __name__ == '__main__': unittest.main()
