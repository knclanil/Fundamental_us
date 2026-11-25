import unittest
from fundamentals.financial_repair import verified_equity_replacement, eps_gap_reviews

class AccuracyTests(unittest.TestCase):
    def test_eps_missing_is_reported(self):
        old={'period_end':'2025-12-31','metrics':{}}
        candidate={'metrics':{},'metric_sources':{}}
        rows=eps_gap_reviews(old,candidate,'TEST',123,'annual')
        self.assertEqual({r['metric'] for r in rows},{'eps_basic','eps_diluted'})
        self.assertTrue(all(r['status']=='EPS_SOURCE_MISSING_REVIEW' for r in rows))

    def test_equity_requires_same_accession(self):
        old={'period_end':'2025-12-31','metrics':{'assets':100,'liabilities':60,'equity':-20}}
        candidate={'metrics':{'assets':100,'liabilities':60,'equity':40},'metric_sources':{
            k:{'accession':('different' if k=='equity' else 'same'),'end':'2025-12-31','tag':k}
            for k in ('assets','liabilities','equity')}}
        self.assertIsNone(verified_equity_replacement(old,candidate))
        candidate['metric_sources']['equity']['accession']='same'
        self.assertIsNotNone(verified_equity_replacement(old,candidate))

    def test_equity_nci_blocks_replacement(self):
        old={'period_end':'2025-12-31','metrics':{'assets':100,'liabilities':60,'equity':-20}}
        candidate={'metrics':{'assets':100,'liabilities':60,'equity':40,'equity_including_nci':40},
                   'metric_sources':{k:{'accession':'same','end':'2025-12-31','tag':k} for k in ('assets','liabilities','equity')}}
        self.assertIsNone(verified_equity_replacement(old,candidate))

if __name__=='__main__': unittest.main()
