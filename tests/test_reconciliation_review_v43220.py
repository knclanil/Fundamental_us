import unittest
from fundamentals.balance_sheet import reconciliation_diagnostics

class ReconciliationReviewTests(unittest.TestCase):
    def test_alternatives_do_not_change_metrics(self):
        metrics={'assets':100,'liabilities':60,'equity':30,'noncontrolling_interest':10}
        original=metrics.copy()
        d=reconciliation_diagnostics(metrics)
        self.assertEqual(metrics,original)
        self.assertEqual(d['reported']['status'],'reconciled')
        self.assertTrue(any(a['equation']=='parent_equity_plus_nci' and a['within_tolerance'] for a in d['alternatives']))
    def test_reported_source_total_is_diagnostic_only(self):
        m={'assets':100,'liabilities':50,'equity':20,'liabilities_and_stockholders_equity':100}
        d=reconciliation_diagnostics(m)
        self.assertEqual(d['reported']['status'],'unreconciled')
        self.assertTrue(any(a['equation']=='sec_reported_liabilities_and_equity_total' and a['within_tolerance'] for a in d['alternatives']))
        self.assertEqual(m['liabilities'],50)
if __name__=='__main__': unittest.main()
