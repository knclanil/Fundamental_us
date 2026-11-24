import unittest
from datetime import date,datetime,timedelta,timezone
from fundamentals.normalize import normalize
from fundamentals.universe import parse_cap,join_sec
from fundamentals.collect import aware,due

class LargeCapTests(unittest.TestCase):
    def test_cap(self):
        self.assertEqual(parse_cap('$12.5B'),12_500_000_000)
        self.assertEqual(parse_cap('10000000000'),10_000_000_000)
        self.assertIsNone(parse_cap('N/A'))
    def test_sec_join(self):
        self.assertEqual(join_sec([{'ticker':'AAPL','market_cap':1e12}],[{'ticker':'AAPL','cik_str':320193,'title':'Apple'}])[0]['cik'],320193)
    def test_datetime(self):
        self.assertEqual(aware(datetime(2026,1,1)).tzinfo,timezone.utc)
        self.assertTrue(due({'last_success_at':datetime(2020,1,1)},7))
        self.assertFalse(due({'last_success_at':datetime.now(timezone.utc)},7))
    def test_normalize(self):
        payload={'facts':{'us-gaap':{'NetIncomeLoss':{'units':{'USD':[
          {'start':'2025-01-01','end':'2025-12-31','filed':'2026-02-01','form':'10-K','frame':'CY2025','val':100},
          {'start':'2010-01-01','end':'2010-12-31','filed':'2011-02-01','form':'10-K','frame':'CY2010','val':1}]}}}}}
        rows=normalize(payload,5,date(2026,11,24))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['metrics']['net_income'],100)
    def test_quarterly_cash_flow(self):
        payload={'facts':{'us-gaap':{'NetCashProvidedByUsedInOperatingActivities':{'units':{'USD':[
          {'start':'2025-01-01','end':'2025-03-31','filed':'2025-05-01','form':'10-Q','frame':'CY2025Q1','val':30},
          {'start':'2025-01-01','end':'2025-06-30','filed':'2025-08-01','form':'10-Q','frame':'CY2025Q2','val':60}]}}}}}
        rows=normalize(payload,5,date(2026,11,24))
        self.assertEqual(len(rows),2)

if __name__=='__main__':unittest.main()
