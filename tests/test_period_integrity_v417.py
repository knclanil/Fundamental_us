import unittest
from datetime import date
from fundamentals.normalize import normalize

def item(start,end,fy,fp,form,val):
    return {'start':start,'end':end,'fy':fy,'fp':fp,'form':form,'val':val,
            'filed':'2026-11-01','accn':'test'}
def payload(revenues, cash):
    return {'facts':{'us-gaap':{
        'Revenues':{'units':{'USD':revenues}},
        'NetCashProvidedByUsedInOperatingActivities':{'units':{'USD':cash}}}}}

class PeriodIntegrityTests(unittest.TestCase):
    def test_prior_year_comparatives_never_used_for_current_q3(self):
        revenues=[item('2026-04-01','2026-06-30',2026,'Q2','10-Q',200),
                  item('2026-07-01','2026-09-30',2026,'Q3','10-Q',300)]
        cash=[item('2025-01-01','2025-06-30',2026,'Q2','10-Q',100),
              item('2025-01-01','2025-09-30',2026,'Q3','10-Q',180)]
        rows=normalize(payload(revenues,cash),today=date(2026,11,24))
        q3=next(r for r in rows if r['period_end']=='2026-09-30')
        self.assertNotIn('operating_cash_flow',q3['metrics'])
        self.assertNotIn('free_cash_flow',q3['metrics'])
        self.assertFalse(any(r['period_end']=='2025-09-30' for r in rows))

    def test_current_year_ytd_q3(self):
        revenues=[item('2026-01-01','2026-03-31',2026,'Q1','10-Q',100),
                  item('2026-04-01','2026-06-30',2026,'Q2','10-Q',200),
                  item('2026-07-01','2026-09-30',2026,'Q3','10-Q',300)]
        cash=[item('2026-01-01','2026-03-31',2026,'Q1','10-Q',50),
              item('2026-01-01','2026-06-30',2026,'Q2','10-Q',150),
              item('2026-01-01','2026-09-30',2026,'Q3','10-Q',280)]
        rows=normalize(payload(revenues,cash),today=date(2026,11,24))
        q3=next(r for r in rows if r['period_end']=='2026-09-30')
        self.assertEqual(q3['metrics']['operating_cash_flow'],130)
        self.assertEqual(q3['metric_sources']['operating_cash_flow']['current']['end'],'2026-09-30')

    def test_different_fiscal_start_rejected(self):
        revenues=[item('2026-04-01','2026-06-30',2026,'Q2','10-Q',200),
                  item('2026-07-01','2026-09-30',2026,'Q3','10-Q',300)]
        cash=[item('2026-02-01','2026-06-30',2026,'Q2','10-Q',150),
              item('2026-01-01','2026-09-30',2026,'Q3','10-Q',280)]
        rows=normalize(payload(revenues,cash),today=date(2026,11,24))
        q3=next(r for r in rows if r['period_end']=='2026-09-30')
        self.assertNotIn('operating_cash_flow',q3['metrics'])

if __name__=='__main__':unittest.main()
