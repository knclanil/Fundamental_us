import unittest
from fundamentals.repair_validation import validate

class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.old={'period_type':'quarterly','fiscal_year':2025,'fiscal_period':'Q4','period_end':'2025-12-31','metrics':{'assets':100,'liabilities':60}}
        self.candidate=dict(self.old)
    def test_valid_snapshot(self):
        item={'value':40,'source':{'method':'fiscal_year_end_snapshot','annual':{'tag':'StockholdersEquity','accession':'123','end':'2025-12-31','start':None}}}
        approved,decisions=validate(self.old,self.candidate,{'equity':item})
        self.assertIn('equity',approved)
        self.assertEqual(decisions['equity'][0],'PASS')
    def test_bad_balance_blocked(self):
        item={'value':10,'source':{'method':'fiscal_year_end_snapshot','annual':{'tag':'StockholdersEquity','accession':'123','end':'2025-12-31','start':None}}}
        approved,decisions=validate(self.old,self.candidate,{'equity':item})
        self.assertNotIn('equity',approved)
        self.assertEqual(decisions['equity'][0],'REVIEW')
    def test_missing_accession_review(self):
        item={'value':40,'source':{'method':'fiscal_year_end_snapshot','annual':{'tag':'StockholdersEquity','end':'2025-12-31','start':None}}}
        approved,decisions=validate(self.old,self.candidate,{'equity':item})
        self.assertFalse(approved)
        self.assertEqual(decisions['equity'][0],'REVIEW')
    def test_period_mismatch_fail(self):
        item={'value':40,'source':{'method':'fiscal_year_end_snapshot','annual':{'tag':'StockholdersEquity','accession':'123','end':'2025-12-31','start':None}}}
        bad=dict(self.candidate,fiscal_year=2024)
        approved,decisions=validate(self.old,bad,{'equity':item})
        self.assertFalse(approved)
        self.assertEqual(decisions['equity'][0],'FAIL')
if __name__=='__main__': unittest.main()
