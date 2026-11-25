"""v4.1.8.4: no annual filing, quarterly-only and empty SEC data."""
import unittest
from datetime import date
from fundamentals.normalize import normalize
from fundamentals.collect import classify_periods

TODAY=date(2026,11,24)

def observation(start,end,fp,val):
    return {'start':start,'end':end,'filed':'2026-10-20','form':'10-Q',
            'fy':2026,'fp':fp,'val':val,'accn':'0000000000-26-000001'}

def facts(items):
    return {'facts':{'us-gaap':{'Revenues':{'units':{'USD':items}}}}}

class PartialHistoryTests(unittest.TestCase):
    def test_quarterly_only_is_partial(self):
        payload=facts([observation('2026-01-01','2026-03-31','Q1',100),
                       observation('2026-04-01','2026-06-30','Q2',120),
                       observation('2026-07-01','2026-09-30','Q3',140)])
        rows=normalize(payload,years=5,today=TODAY)
        self.assertEqual(classify_periods(rows),('partial',0,3))
        self.assertEqual({r['fiscal_period'] for r in rows},{'Q1','Q2','Q3'})
        self.assertTrue(all(r['metric_sources']['revenue']['form']=='10-Q' for r in rows))
    def test_empty_source_insufficient(self):
        self.assertEqual(classify_periods(normalize(facts([]),today=TODAY)),('insufficient_data',0,0))
    def test_annual_and_quarterly_is_success(self):
        rows=[{'period_type':'annual'},{'period_type':'quarterly'}]
        self.assertEqual(classify_periods(rows),('success',1,1))
    def test_no_fabricated_annual(self):
        rows=normalize(facts([observation('2026-01-01','2026-03-31','Q1',100)]),today=TODAY)
        self.assertFalse(any(r['period_type']=='annual' for r in rows))
        self.assertEqual(classify_periods(rows)[0],'partial')

if __name__=='__main__':unittest.main()
