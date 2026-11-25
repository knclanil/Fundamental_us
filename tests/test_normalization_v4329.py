"""v4.3.2.9: conservative EPS source and dimension regression tests."""
import unittest
from datetime import date
from fundamentals.normalize import normalize, _eligible_companyfacts_observation
from fundamentals.balance_sheet import assess, enrich_balance_sheet

END='2023-10-31'; START='2022-11-01'
def obs(val, tag=None, **kwargs):
    return {'val':val,'start':START,'end':END,'filed':'2023-12-15',
            'form':'10-K','fy':2023,'fp':'FY','accn':'0001-23-000001',**kwargs}

def fixture(*, direct=False, missing_discontinued=False):
    tags={
      'NetIncomeLoss':{'units':{'USD':[obs(100)]}},
      'IncomeLossFromContinuingOperationsPerDilutedShare':{'units':{'USD/shares':[obs(2.0)]}},
      'IncomeLossFromDiscontinuedOperationsNetOfTaxPerDilutedShare':{'units':{'USD/shares':[obs(.25)]}},
      'IncomeLossFromContinuingOperationsPerBasicShare':{'units':{'USD/shares':[obs(2.2)]}},
      'IncomeLossFromDiscontinuedOperationsNetOfTaxPerBasicShare':{'units':{'USD/shares':[obs(.3)]}},
    }
    if direct:tags['EarningsPerShareDiluted']={'units':{'USD/shares':[obs(2.5)]}}
    if missing_discontinued:tags.pop('IncomeLossFromDiscontinuedOperationsNetOfTaxPerDilutedShare')
    return {'facts':{'us-gaap':tags}}

class TestNormalization(unittest.TestCase):
    def test_explicit_dimension_rejected(self):
        self.assertFalse(_eligible_companyfacts_observation({'segment':{'axis':'member'}}))
        self.assertFalse(_eligible_companyfacts_observation({'dimensions':{'axis':'member'}}))
    def test_missing_dimensions_not_verified(self):
        self.assertTrue(_eligible_companyfacts_observation({}))
    def test_eps_both_components(self):
        rows=normalize(fixture(),years=5,today=date(2024,1,1))
        row=next(r for r in rows if r['period_type']=='annual')
        self.assertAlmostEqual(row['metrics']['eps_diluted'],2.25)
        self.assertAlmostEqual(row['metrics']['eps_basic'],2.5)
        self.assertTrue(row['metric_sources']['eps_diluted']['review_required'])
    def test_direct_eps_preferred(self):
        row=next(r for r in normalize(fixture(direct=True),years=5,today=date(2024,1,1)) if r['period_type']=='annual')
        self.assertEqual(row['metrics']['eps_diluted'],2.5)
    def test_missing_discontinued_not_assumed_zero(self):
        row=next(r for r in normalize(fixture(missing_discontinued=True),years=5,today=date(2024,1,1)) if r['period_type']=='annual')
        self.assertNotIn('eps_diluted',row['metrics'])
    def test_no_forced_reconciliation(self):
        m={'assets':100,'liabilities':80,'equity':15}
        enrich_balance_sheet(m)
        self.assertEqual(m['liabilities'],80)
        self.assertEqual(assess(m)['status'],'unreconciled')

if __name__=='__main__': unittest.main()
