"""v4.1.8.3 source inventory tests: no network or database needed."""
import unittest
from datetime import date
from fundamentals.sec_inventory import inventory

class InventoryTests(unittest.TestCase):
    def test_empty_facts(self):
        report = inventory({'cik': 1, 'facts': {}}, date(2026, 11, 25))
        self.assertEqual(report['namespaces'], {})
        self.assertEqual(report['annual_10k_observations'], 0)
    def test_annual_recognition_and_dates(self):
        payload = {'cik': 42, 'entityName': 'Sample', 'facts': {'us-gaap': {'Assets': {'units': {'USD': [
            {'form':'10-K', 'end':'2025-12-31', 'filed':'2026-02-01', 'val':42},
            {'form':'10-Q', 'end':'2026-03-31', 'filed':'2026-05-01', 'val':43}]}}}, 'dei': {}}}
        report = inventory(payload, date(2026, 11, 25))
        self.assertEqual(report['annual_10k_observations'], 1)
        self.assertEqual(report['recent_10k_observations'], 1)
        self.assertEqual(report['recognized_metric_tags']['assets'], ['Assets'])
        self.assertEqual(report['form_counts']['10-Q'], 1)
    def test_future_filing_not_recent(self):
        payload={'facts':{'us-gaap':{'NetIncomeLoss':{'units':{'USD':[{'form':'10-K','end':'2026-12-31','filed':'2027-02-01','start':'2026-01-01'}]}}}}}
        report=inventory(payload,date(2026,11,25))
        self.assertEqual(report['recent_10k_observations'],0)
        self.assertEqual(report['annual_10k_observations'],1)

if __name__ == '__main__': unittest.main()
