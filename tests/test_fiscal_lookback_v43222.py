import unittest
from datetime import date
from fundamentals.normalize import normalize
from fundamentals.fact_alignment import align_balance_sheet

class FiscalLookbackTests(unittest.TestCase):
    def test_five_fiscal_years_not_calendar_cutoff(self):
        observations=[]
        for year in range(2021,2026):
            observations.append({'start':f'{year-1}-11-01','end':f'{year}-10-31',
                'filed':f'{year}-12-15','form':'10-K','fy':year,'fp':'FY',
                'accn':f'{year}-annual','val':100+year})
        payload={'facts':{'us-gaap':{'NetIncomeLoss':{'units':{'USD':observations}}}}}
        rows=normalize(payload,years=5,today=date(2026,11,26))
        annual=[r for r in rows if r['period_type']=='annual']
        self.assertEqual(len(annual),5)
        self.assertEqual([r['fiscal_year'] for r in annual],[2021,2022,2023,2024,2025])

    def test_missing_component_recovered_from_single_filing(self):
        row={'period_end':'2023-10-31','period_type':'annual',
             'metrics':{'assets':100,'equity':60},'metric_sources':{}}
        facts=[{'metric':k,'tag':k,'val':v,'end':'2023-10-31',
            'filed':date(2024,12,20),'form':'10-K','accn':'verified', 'rank':0}
            for k,v in [('assets',100),('liabilities',40),('equity',60)]]
        self.assertTrue(align_balance_sheet(row,facts))
        self.assertEqual(row['metrics']['liabilities'],40)

if __name__=='__main__':unittest.main()
