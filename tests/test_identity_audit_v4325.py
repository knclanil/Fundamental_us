import unittest
from fundamentals.quality_audit import identity, generate

class Collection:
    def __init__(self,rows): self.rows=rows
    def find(self,*a,**k): return list(self.rows)
class DB:
    def __init__(self):
        self.companies=Collection([{'_id':1,'ticker':'AAPL','cik':'0000320193'}])
        self.financial_annual=Collection([{'cik':320193,'period_end':'2025-12-31','metrics':{'assets':100,'liabilities':60,'equity':40}}])
        self.financial_quarterly=Collection([{'cik':'320193','period_end':'2025-09-30','metrics':{}}])
        self.largecap_collection_state=Collection([{'_id':320193,'reporting_status':'success'}])
class Tests(unittest.TestCase):
    def test_cik_padding(self):
        self.assertEqual(identity({'cik':320193}), '0000320193')
        self.assertEqual(identity({'cik':'0000320193'}), '0000320193')
    def test_merges_identity_without_writing(self):
        db=DB(); result=generate(db)
        self.assertEqual(len(result['companies']),1)
        self.assertEqual(result['companies'][0]['ticker'],'AAPL')
        self.assertEqual(result['summary']['annual_documents'],1)
        self.assertEqual(result['summary']['tracked_collector_companies'],1)
    def test_detects_duplicate_profiles(self):
        db=DB();db.companies.rows.append({'_id':2,'ticker':'DUP','cik':320193})
        result=generate(db)
        self.assertEqual(result['summary']['identity_collision_count'],1)
        self.assertEqual(result['summary']['annual_documents'],1)
if __name__=='__main__':unittest.main()
