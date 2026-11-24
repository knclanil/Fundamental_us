import unittest
from datetime import timedelta
from v4_mongodb.collector import flatten_facts, is_due, parse_universe, now

class CollectorTests(unittest.TestCase):
    def test_parse_universe(self):
        data = {'fields': ['cik', 'name', 'ticker', 'exchange'], 'data': [[320193, 'Apple Inc.', 'AAPL', 'Nasdaq']]}
        self.assertEqual(parse_universe(data)[0]['ticker'], 'AAPL')
    def test_flatten_facts(self):
        raw = {'facts': {'us-gaap': {'Assets': {'label': 'Assets', 'units': {'USD': [{'val': 12}]}}}}}
        docs = list(flatten_facts(raw, 320193))
        self.assertEqual(docs[0]['_id'], '320193:us-gaap:Assets:USD')
        self.assertEqual(docs[0]['observations'][0]['val'], 12)
    def test_due_new(self):
        self.assertTrue(is_due(None, 7))
    def test_due_recent(self):
        self.assertFalse(is_due({'last_success_at': now()}, 7))
    def test_due_old(self):
        self.assertTrue(is_due({'last_success_at': now()-timedelta(days=9)}, 7))
    def test_retry_cooldown(self):
        self.assertFalse(is_due({'next_retry_at': now()+timedelta(hours=1)}, 0))
