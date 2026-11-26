import unittest
from datetime import date
from fundamentals.fact_alignment import align_balance_sheet

class FactAlignmentTests(unittest.TestCase):
    def test_replaces_mixed_accession_with_reconciled_filing(self):
        row={'period_end':'2023-10-31','period_type':'annual','metrics':{'assets':100,'liabilities':40,'equity':600},'metric_sources':{}}
        facts=[{'metric':k,'tag':k,'val':v,'end':'2023-10-31','filed':date(2024,12,20),
                'form':'10-K','accn':'good','rank':0} for k,v in [('assets',100),('liabilities',40),('equity',60)]]
        self.assertTrue(align_balance_sheet(row,facts))
        self.assertEqual(row['metrics']['equity'],60)
        self.assertEqual(row['metric_sources']['equity']['accession'],'good')
    def test_never_forces_unreconciled_filing(self):
        row={'period_end':'2023-10-31','period_type':'annual','metrics':{'assets':100,'liabilities':40,'equity':600},'metric_sources':{}}
        facts=[{'metric':k,'tag':k,'val':v,'end':'2023-10-31','filed':date(2024,12,20),
                'form':'10-K','accn':'bad','rank':0} for k,v in [('assets',100),('liabilities',40),('equity',50)]]
        self.assertFalse(align_balance_sheet(row,facts))
        self.assertEqual(row['metrics']['equity'],600)

if __name__=='__main__':unittest.main()
