from datetime import date
from fundamentals.normalize import normalize

def fact(start,end,fy,fp,form,val):
    return {'start':start,'end':end,'fy':fy,'fp':fp,'form':form,'val':val,'filed':'2026-11-01','accn':'test'}

def test_ytd_and_q4_cashflows():
    entries=[fact('2026-01-01','2026-03-31',2026,'Q1','10-Q',100),
             fact('2026-01-01','2026-06-30',2026,'Q2','10-Q',250),
             fact('2026-01-01','2026-09-30',2026,'Q3','10-Q',430),
             fact('2026-01-01','2026-12-31',2026,'FY','10-K',620)]
    payload={'facts':{'us-gaap':{'NetCashProvidedByUsedInOperatingActivities':{'units':{'USD':entries}},
            'PaymentsToAcquirePropertyPlantAndEquipment':{'units':{'USD':[{**x,'val':v} for x,v in zip(entries,[20,45,75,110])]}},
            'Revenues':{'units':{'USD':[fact('2026-01-01','2026-12-31',2026,'FY','10-K',1000)]}}}}}
    rows=normalize(payload,years=5,today=date(2026,12,31))
    q={r['fiscal_period']:r for r in rows if r['period_type']=='quarterly'}
    assert [q[k]['metrics']['operating_cash_flow'] for k in ('Q1','Q2','Q3','Q4')]==[100,150,180,190]
    assert [q[k]['metrics']['capex'] for k in ('Q1','Q2','Q3','Q4')]==[20,25,30,35]
    assert q['Q3']['metrics']['free_cash_flow']==150
    assert q['Q4']['metric_sources']['operating_cash_flow']['method']=='annual_minus_q3_ytd'

def test_no_unsupported_ytd_difference():
    payload={'facts':{'us-gaap':{'NetCashProvidedByUsedInOperatingActivities':{'units':{'USD':[
        fact('2026-01-01','2026-09-30',2026,'Q3','10-Q',430)]}}}}}
    assert normalize(payload,years=5,today=date(2026,11,24))==[]
