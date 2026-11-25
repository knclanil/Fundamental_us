import unittest
from fundamentals.balance_sheet import assess,enrich_balance_sheet
from fundamentals.quality_audit import analyze_company
class BalanceTests(unittest.TestCase):
    def test_nci(self):
        self.assertEqual(assess({'assets':100,'liabilities':60,'equity':35,'noncontrolling_interest':3,'redeemable_nci':2})['status'],'reconciled')
    def test_derived_components(self):
        m={'assets':100,'equity':40,'current_liabilities':20,'liabilities_noncurrent':40}
        enrich_balance_sheet(m,{})
        self.assertEqual(m['liabilities'],60)
    def test_residual_candidate_not_auto_written(self):
        m={'assets':100,'equity':40};enrich_balance_sheet(m,{})
        self.assertNotIn('liabilities',m)
        self.assertEqual(m['liabilities_derivation_candidate'],60)
    def test_outlier(self):
        self.assertEqual(assess({'assets':100,'liabilities':99999,'equity':10})['status'],'scale_outlier')
    def test_spinoff_info(self):
        r=analyze_company({'cik':'1','ticker':'HONA','is_spinoff':True},[],[])
        self.assertEqual(r['issue_count'],0)
        self.assertEqual(len(r['informational_notes']),2)
if __name__=='__main__':unittest.main()
