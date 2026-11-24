import unittest
from datetime import date,datetime,timezone
from fundamentals.normalize import normalize
from fundamentals.collect import aware,due
from fundamentals.universe import parse_cap,join_sec,parse_wikipedia,fetch_large_caps

TODAY=date(2026,11,24)
def item(start,end,fy,fp,form,val,tag_frame=None):
    out={'end':end,'filed':'2026-11-01','form':form,'fy':fy,'fp':fp,'val':val,'accn':'0000000000-26-000001'}
    if start:out['start']=start
    if tag_frame:out['frame']=tag_frame
    return out

def payload(mapping):
    return {'facts':{'us-gaap':{k:{'units':{'USD':v}} for k,v in mapping.items()}}}

class LargeCapTests(unittest.TestCase):
    def test_fiscal_august_year(self):
        p=payload({'Revenues':[item('2025-09-01','2026-08-31',2026,'FY','10-K',74183445000,'CY2026')]})
        rows=normalize(p,5,TODAY)
        self.assertEqual(rows[0]['period'],'FY2026')
        self.assertEqual(rows[0]['period_end'],'2026-08-31')
        self.assertEqual(rows[0]['metric_sources']['revenue']['form'],'10-K')
    def test_balance_sheet_and_source(self):
        p=payload({'Assets':[item(None,'2026-08-31',2026,'FY','10-K',500)],
                   'Liabilities':[item(None,'2026-08-31',2026,'FY','10-K',300)],
                   'StockholdersEquity':[item(None,'2026-08-31',2026,'FY','10-K',200)]})
        r=normalize(p,5,TODAY)[0]
        self.assertEqual(r['metrics']['assets'],500)
        self.assertEqual(r['metrics']['liabilities'],300)
        self.assertEqual(r['metrics']['equity'],200)
        self.assertEqual(r['metric_sources']['assets']['accession'],'0000000000-26-000001')
    def test_quarter_ytd_rejected(self):
        p=payload({'NetCashProvidedByUsedInOperatingActivities':[
            item('2026-01-01','2026-03-31',2026,'Q1','10-Q',30),
            item('2026-01-01','2026-06-30',2026,'Q2','10-Q',60),
            item('2026-04-01','2026-06-30',2026,'Q2','10-Q',35)]})
        r=normalize(p,5,TODAY)
        self.assertEqual(len(r),2)
        self.assertEqual(next(x for x in r if x['fiscal_period']=='Q2')['metrics']['operating_cash_flow'],35)
    def test_no_invented_quarter_four(self):
        p=payload({'NetIncomeLoss':[item('2025-09-01','2026-08-31',2026,'FY','10-K',100)]})
        self.assertEqual([r['period'] for r in normalize(p,5,TODAY)],['FY2026'])
    def test_missing_not_zero(self):
        p=payload({'Revenues':[item('2025-09-01','2026-08-31',2026,'FY','10-K',100)]})
        self.assertNotIn('assets',normalize(p,5,TODAY)[0]['metrics'])
    def test_old_five_year_cutoff(self):
        p=payload({'Revenues':[item('2018-01-01','2018-12-31',2018,'FY','10-K',10),item('2025-01-01','2025-12-31',2025,'FY','10-K',20)]})
        self.assertEqual(len(normalize(p,5,TODAY)),1)
    def test_cap(self):self.assertEqual(parse_cap('$12.5B'),12_500_000_000)
    def test_sec_join(self):self.assertEqual(join_sec([{'ticker':'AAPL','market_cap':1e12}],[{'ticker':'AAPL','cik_str':320193,'title':'Apple'}])[0]['cik'],320193)
    def test_datetime(self):
        self.assertEqual(aware(datetime(2026,1,1)).tzinfo,timezone.utc)
        self.assertTrue(due({'last_success_at':datetime(2020,1,1)},7))
    def test_reject_short_html(self):
        with self.assertRaises(ValueError):parse_wikipedia('<html><body>Blocked</body></html>')
    def test_bootstrap_fallback(self):
        from unittest.mock import Mock
        import requests
        session=Mock();session.get.side_effect=requests.ConnectionError('blocked')
        self.assertEqual(fetch_large_caps(session=session)[0]['universe_source'],'bootstrap_partial')

if __name__=='__main__':unittest.main()

class MigrationTests(unittest.TestCase):
    def test_best_document_has_more_metrics(self):
        from fundamentals.migrate import score
        a={'_id':1,'metrics':{'revenue':10}}
        b={'_id':2,'metrics':{'revenue':10,'assets':20}}
        self.assertGreater(score(b),score(a))
    def test_migration_empty_collection(self):
        from unittest.mock import MagicMock
        from fundamentals.migrate import migrate_collection
        db=MagicMock()
        db.__getitem__.return_value.aggregate.return_value=iter([])
        result=migrate_collection(db,'financial_quarterly')
        self.assertEqual(result['removed'],0)
        db.__getitem__.return_value.create_index.assert_called_once()
