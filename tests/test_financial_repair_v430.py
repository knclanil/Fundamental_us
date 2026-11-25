import unittest
from fundamentals.financial_repair import plan,check_candidate_balance,safe_update

class RepairTests(unittest.TestCase):
    def test_only_missing_metrics(self):
        old={'metrics':{'revenue':100,'net_income':None},'metric_sources':{}}
        new={'metrics':{'revenue':101,'net_income':20,'eps_diluted':2},
             'metric_sources':{'revenue':{'tag':'a'},'net_income':{'tag':'b'},'eps_diluted':{'tag':'c'}}}
        additions,conflicts,_=plan(old,new)
        self.assertEqual(set(additions),{'net_income','eps_diluted'})
        self.assertEqual(len(conflicts),1)
    def test_no_unprovenanced_additions(self):
        additions,_,_=plan({'metrics':{}},{'metrics':{'revenue':100},'metric_sources':{}})
        self.assertFalse(additions)
    def test_balance_guard(self):
        old={'metrics':{'assets':100,'liabilities':60},'period_end':'2025-12-31'}
        self.assertTrue(check_candidate_balance(old,{'equity':{'value':40}}))
        self.assertFalse(check_candidate_balance(old,{'equity':{'value':10}}))
    def test_safe_update_has_atomic_guards(self):
        class Result: modified_count=1
        class Fake:
            def update_one(self,selector,update):
                self.assertion=(selector,update)
                return Result()
        coll=Fake()
        self.assertEqual(safe_update(coll,{'_id':7},'revenue',100,{'tag':'a'}),1)
        selector,update=coll.assertion
        self.assertIn('$and',selector)
        self.assertEqual(update['$set']['metrics.revenue'],100)

if __name__=='__main__':unittest.main()
