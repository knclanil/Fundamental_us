"""v4.1.8.1 regression tests for sparse SEC fact payloads."""
import unittest
from datetime import date
from fundamentals.normalize import normalize

TODAY=date(2026,11,24)

def fact(end, form, fp, val, start=None):
    x={'end':end,'form':form,'fp':fp,'fy':2026,'val':val,
       'filed':'2026-11-01','accn':'fixture'}
    if start: x['start']=start
    return x

def payload(**tags):
    return {'facts':{'us-gaap':{tag:{'units':{'USD':values}}
                               for tag,values in tags.items()}}}

class SparseCalendarHotfixTests(unittest.TestCase):
    def test_annual_instant_only_10k(self):
        rows=normalize(payload(Assets=[fact('2026-08-31','10-K','FY',500)],
                               Liabilities=[fact('2026-08-31','10-K','FY',300)]),today=TODAY)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['period'],'FY2026')
        self.assertEqual(rows[0]['metrics']['assets'],500)

    def test_q1_cashflow_only_can_anchor_quarter(self):
        rows=normalize(payload(NetCashProvidedByUsedInOperatingActivities=[
            fact('2026-03-31','10-Q','Q1',30,'2026-01-01'),
            fact('2026-06-30','10-Q','Q2',60,'2026-01-01'),
            fact('2026-06-30','10-Q','Q2',35,'2026-04-01')]),today=TODAY)
        self.assertEqual({r['period'] for r in rows},{'FY2026Q1','FY2026Q2'})
        self.assertEqual(next(r for r in rows if r['period']=='FY2026Q2')['metrics']['operating_cash_flow'],35)

    def test_10q_comparative_instant_not_calendar_anchor(self):
        rows=normalize(payload(Assets=[fact('2021-12-31','10-Q','Q3',500)]),today=TODAY)
        self.assertEqual(rows,[])

if __name__=='__main__':unittest.main()
