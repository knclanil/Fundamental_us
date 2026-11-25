import unittest
from fundamentals.cik_sync import normalize_ticker, cik10, issuer_guard, resolve_issuer
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
    def test_xom_override(self):
        result, conflict = resolve_issuer('XOM', {'cik':'0002115436','sec_name':'ExxonMobil Holdings Corp'})
        self.assertIsNotNone(conflict)
        self.assertEqual(result['cik'], '0000034088')
        self.assertEqual(result['resolution_source'], 'verified_parent_override')
    def test_normal_mapping(self):
        result, conflict = resolve_issuer('AAPL', {'cik':'0000320193','sec_name':'Apple Inc.'})
        self.assertIsNone(conflict)
        self.assertEqual(result['cik'], '0000320193')
if __name__ == '__main__': unittest.main()
