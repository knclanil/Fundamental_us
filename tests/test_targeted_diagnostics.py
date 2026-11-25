import unittest
from fundamentals.normalize import diagnose_annual

class DiagnosticsTests(unittest.TestCase):
    def test_empty_facts(self):
        d=diagnose_annual({'facts':{'us-gaap':{}}})
        self.assertIsNone(d['fiscal_anchor'])
        self.assertEqual(d['counts'],{})
    def test_outside_window(self):
        p={'facts':{'us-gaap':{'Revenues':{'units':{'USD':[{'form':'10-K','start':'2010-01-01','end':'2010-12-31','filed':'2011-02-01'}]}}}}}
        d=diagnose_annual(p,years=5)
        self.assertEqual(d['counts']['outside_window'],1)
    def test_recent_annual(self):
        p={'facts':{'us-gaap':{'Revenues':{'units':{'USD':[{'form':'10-K','start':'2025-01-01','end':'2025-12-31','filed':'2026-02-01'}]}}}}}
        d=diagnose_annual(p,years=5)
        self.assertEqual(d['counts']['candidate_annual_facts'],1)

if __name__=='__main__':unittest.main()
