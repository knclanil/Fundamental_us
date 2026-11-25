"""v4.3.2.6: regression tests for SEC repair identity and write safety."""
import unittest
from unittest.mock import MagicMock, patch
from fundamentals.financial_repair import plan, repair_company

class Repair326Tests(unittest.TestCase):
    def test_non_null_values_are_never_overwritten(self):
        existing={'metrics':{'eps_basic':2.0}}
        candidate={'metrics':{'eps_basic':3.0},'metric_sources':{'eps_basic':{'tag':'EarningsPerShareBasic'}}}
        additions,conflicts,_=plan(existing,candidate)
        self.assertNotIn('eps_basic',additions)
        self.assertEqual(conflicts[0]['stored'],2.0)

    def test_missing_eps_with_sec_source_is_proposed(self):
        old={'metrics':{'eps_basic':None}}
        new={'metrics':{'eps_basic':3.0},'metric_sources':{'eps_basic':{'tag':'EarningsPerShareBasic'}}}
        additions,_,_=plan(old,new)
        self.assertEqual(additions['eps_basic']['value'],3.0)

    @patch('fundamentals.financial_repair.normalize',return_value=[])
    def test_repair_uses_profile_cik_not_profile_id(self,_):
        db=MagicMock(); db.financial_annual.find.return_value=[];db.financial_quarterly.find.return_value=[]
        sec=MagicMock();sec.company_facts.return_value={'cik':320193,'facts':{}}
        repair_company(db,sec,{'_id':'profile-uuid','ticker':'AAPL','cik':'0000320193'})
        sec.company_facts.assert_called_once_with(320193)

if __name__=='__main__':unittest.main()
