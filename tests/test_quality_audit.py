import csv
import json
import tempfile
import unittest
from pathlib import Path
from fundamentals.quality_audit import analyze_company,generate,write_reports

class Collection:
    def __init__(self,rows):self.rows=rows
    def find(self,*args,**kwargs):return list(self.rows)
class Database:
    def __init__(self):
        self.companies=Collection([{'_id':1,'ticker':'ABC','name':'Example'}])
        self.financial_annual=Collection([{'cik':1,'period_type':'annual','period_end':'2025-12-31','metrics':{'assets':100,'liabilities':60,'equity':40}}])
        self.financial_quarterly=Collection([{'cik':1,'period_type':'quarterly','period_end':'2026-03-31','metrics':{'revenue':0}}])
        self.largecap_collection_state=Collection([{'_id':1,'reporting_status':'success'}])

class AuditTests(unittest.TestCase):
    def test_zero_is_present_and_balance_reconciles(self):
        result=analyze_company({'_id':1,'ticker':'ABC'},[{'cik':1,'metrics':{'assets':100,'liabilities':60,'equity':40}}], [{'cik':1,'metrics':{'revenue':0}}])
        self.assertEqual(result['missing_metric_counts']['revenue'],1)
        self.assertFalse(any(i['code']=='balance_sheet_unreconciled' for i in result['issues']))
    def test_balance_sheet_discrepancy_is_flag_only(self):
        rows=[{'cik':1,'period_end':'2025-12-31','metrics':{'assets':100,'liabilities':60,'equity':30}}]
        result=analyze_company({'_id':1},rows,[])
        self.assertTrue(any(i['code']=='balance_sheet_unreconciled' for i in result['issues']))
        self.assertEqual(rows[0]['metrics']['equity'],30)
    def test_ytd_mismatch(self):
        row={'cik':1,'period_end':'2026-06-30','metric_sources':{'operating_cash_flow':{'method':'ytd_difference','current':{'start':'2026-01-01','end':'2026-06-30'},'previous':{'start':'2025-01-01','end':'2026-03-31'}}}}
        result=analyze_company({'_id':1},[],[row])
        self.assertTrue(any(i['code']=='ytd_start_mismatch' for i in result['issues']))
    def test_nested_metrics_zero_and_missing(self):
        result=analyze_company({'_id':1}, [{'cik':1,'metrics':{'revenue':0,'assets':100,'liabilities':60,'equity':40}}], [])
        self.assertEqual(result['missing_metric_counts']['revenue'],0)
        self.assertEqual(result['missing_metric_counts']['net_income'],1)
        self.assertFalse(any(i['code']=='balance_sheet_unreconciled' for i in result['issues']))
    def test_19_quarters_is_not_automatically_an_issue(self):
        rows=[{'cik':1,'period_end':f'2021-{i:02d}-28','metrics':{}} for i in range(1,20)]
        result=analyze_company({'_id':1},[],rows)
        self.assertFalse(any(i['code']=='quarterly_history_short_review' for i in result['issues']))
    def test_stale_company_is_separate_from_collector_state(self):
        db=Database()
        db.companies.rows.append({'_id':999,'ticker':'OLD'})
        report=generate(db)
        self.assertEqual(report['summary']['tracked_collector_companies'],1)
        self.assertEqual(report['summary']['untracked_legacy_or_orphan_companies'],1)
    def test_balance_nested_discrepancy(self):
        result=analyze_company({'_id':1},[{'cik':1,'metrics':{'assets':100,'liabilities':60,'equity':20}}],[])
        self.assertTrue(any(i['code']=='balance_sheet_unreconciled' for i in result['issues']))
    def test_read_only_report_files(self):
        db=Database();report=generate(db)
        self.assertEqual(report['summary']['annual_documents'],1)
        self.assertEqual(report['summary']['quarterly_documents'],1)
        with tempfile.TemporaryDirectory() as folder:
            write_reports(report,folder)
            self.assertEqual(json.loads((Path(folder)/'quality_report.json').read_text())['version'],'4.2.1')
            with (Path(folder)/'company_coverage.csv').open() as handle:
                self.assertEqual(len(list(csv.DictReader(handle))),1)
            self.assertTrue((Path(folder)/'quality_issues.csv').exists())

if __name__=='__main__':unittest.main()
