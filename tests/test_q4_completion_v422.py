import unittest
from datetime import date
from fundamentals.q4_completion import complete_q4
from fundamentals.q4_backfill import plan_company
from fundamentals.normalize import normalize


def source(tag, start, end):
    return {'tag':tag,'start':start,'end':end,'form':'10-Q','filed':'2026-11-01','accession':'fixture'}


def fixtures():
    fy=2025
    ends=['2025-03-31','2025-06-30','2025-09-30']
    starts=['2025-01-01','2025-04-01','2025-07-01']
    quarters=[]
    for i,(st,en) in enumerate(zip(starts,ends)):
        quarters.append({'fiscal_year':fy,'fiscal_period':f'Q{i+1}','period_type':'quarterly',
          'period_end':en,'metrics':{'revenue':100+i*10,'net_income':20+i},
          'metric_sources':{'revenue':source('Revenues',st,en),'net_income':source('NetIncomeLoss',st,en)}})
    annual={'fiscal_year':fy,'fiscal_period':'FY','period_type':'annual','period_end':'2025-12-31',
      'metrics':{'revenue':500,'net_income':100,'assets':400,'liabilities':300,'equity':100,'eps_diluted':2.1},
      'metric_sources':{'revenue':source('Revenues','2025-01-01','2025-12-31'),
       'net_income':source('NetIncomeLoss','2025-01-01','2025-12-31'),
       **{k:source(tag,None,'2025-12-31') for k,tag in [('assets','Assets'),('liabilities','Liabilities'),('equity','StockholdersEquity')]}}}
    q4={'_id':'existing','fiscal_year':fy,'fiscal_period':'Q4','period_type':'quarterly','period_end':'2025-12-31',
        'metrics':{'operating_cash_flow':25,'capex':5,'free_cash_flow':20},'metric_sources':{}}
    return annual,quarters,q4


class Q4Tests(unittest.TestCase):
    def test_income_balance_and_eps_safety(self):
        annual,quarters,_=fixtures();m,s=complete_q4(annual,quarters)
        self.assertEqual(m['revenue'],170)
        self.assertEqual(m['net_income'],37)
        self.assertEqual((m['assets'],m['liabilities'],m['equity']),(400,300,100))
        self.assertNotIn('eps_diluted',m)
        self.assertEqual(s['revenue']['method'],'annual_minus_q1_q2_q3')
        self.assertEqual(s['assets']['method'],'fiscal_year_end_snapshot')

    def test_no_incomplete_quarters(self):
        a,qs,_=fixtures();self.assertEqual(complete_q4(a,qs[:2]),({},{}))

    def test_no_mixed_tags(self):
        a,qs,_=fixtures();qs[1]['metric_sources']['revenue']['tag']='SalesRevenueNet'
        m,_=complete_q4(a,qs);self.assertNotIn('revenue',m);self.assertIn('net_income',m)

    def test_no_ytd_as_standalone(self):
        a,qs,_=fixtures();qs[1]['metric_sources']['revenue']['start']='2025-01-01'
        m,_=complete_q4(a,qs);self.assertNotIn('revenue',m)

    def test_no_mismatched_fiscal_year(self):
        a,qs,_=fixtures();qs[1]['fiscal_year']=2024
        self.assertEqual(complete_q4(a,qs),({},{}))

    def test_no_ambiguous_quarters(self):
        a,qs,_=fixtures();self.assertEqual(complete_q4(a,qs+[dict(qs[1])]),({},{}))

    def test_backfill_preserves_cashflow_and_present_values(self):
        a,qs,q4=fixtures();q4['metrics']['assets']=400
        plans=plan_company([a],qs+[q4]);self.assertEqual(len(plans),1)
        _,m,_=plans[0];self.assertNotIn('assets',m)
        self.assertEqual(q4['metrics']['free_cash_flow'],20)
        self.assertEqual(m['revenue'],170)

    def test_backfill_no_q4_does_not_create(self):
        a,qs,_=fixtures();self.assertEqual(plan_company([a],qs),[])

    def test_normalizer_integration(self):
        def obs(start,end,form,fp,val):
            return {'start':start,'end':end,'form':form,'fy':2025,'fp':fp,
                    'filed':'2026-01-31','accn':'fixture','val':val}
        entries=[obs('2025-01-01','2025-03-31','10-Q','Q1',100),
                 obs('2025-04-01','2025-06-30','10-Q','Q2',110),
                 obs('2025-07-01','2025-09-30','10-Q','Q3',120),
                 obs('2025-01-01','2025-12-31','10-K','FY',500)]
        assets=[{'end':'2025-12-31','form':'10-K','fy':2025,'fp':'FY','filed':'2026-01-31','val':400,'accn':'fixture'}]
        facts={'Revenues':{'units':{'USD':entries}},'Assets':{'units':{'USD':assets}}}
        rows=normalize({'facts':{'us-gaap':facts}},years=5,today=date(2026,2,1))
        q4=next(r for r in rows if r['period']=='FY2025Q4')
        self.assertEqual(q4['metrics']['revenue'],170)
        self.assertEqual(q4['metrics']['assets'],400)

if __name__=='__main__':unittest.main()
