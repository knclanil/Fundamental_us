import unittest
from unittest.mock import Mock
from datetime import datetime, timedelta, timezone
from src.collect import due
from src.sec_client import SecClient

class CoreTests(unittest.TestCase):
    def test_due_when_never_collected(self):
        self.assertTrue(due(None, datetime.now(timezone.utc), 7))
    def test_recent_success_skipped(self):
        now = datetime.now(timezone.utc)
        self.assertFalse(due({"last_success_at": now}, now, 7))
    def test_old_success_due(self):
        now = datetime.now(timezone.utc)
        self.assertTrue(due({"last_success_at": now - timedelta(days=8)}, now, 7))
    def test_retry_cooldown(self):
        now = datetime.now(timezone.utc)
        self.assertFalse(due({"next_retry_at": now + timedelta(hours=1)}, now, 7))
    def test_mongodb_naive_last_success_old(self):
        now = datetime.now(timezone.utc)
        old_naive = (now - timedelta(days=8)).replace(tzinfo=None)
        self.assertTrue(due({"last_success_at": old_naive}, now, 7))

    def test_mongodb_naive_last_success_recent(self):
        now = datetime.now(timezone.utc)
        recent_naive = (now - timedelta(days=1)).replace(tzinfo=None)
        self.assertFalse(due({"last_success_at": recent_naive}, now, 7))

    def test_mongodb_naive_retry(self):
        now = datetime.now(timezone.utc)
        retry_naive = (now + timedelta(hours=2)).replace(tzinfo=None)
        self.assertFalse(due({"next_retry_at": retry_naive}, now, 7))

    def test_aware_non_utc_timezone(self):
        now = datetime.now(timezone.utc)
        other_tz = timezone(timedelta(hours=-5))
        last = (now - timedelta(days=8)).astimezone(other_tz)
        self.assertTrue(due({"last_success_at": last}, now, 7))

    def test_sec_user_agent_validation(self):
        with self.assertRaises(ValueError):
            SecClient("example@example.com")
    def test_sec_client_parses_json(self):
        session = Mock()
        response = Mock(status_code=200)
        response.json.return_value = {"cik": 1}
        session.get.return_value = response
        client = SecClient("MaketData Research researcher@real-domain.org", min_interval=0.1, session=session)
        self.assertEqual(client.company_facts(1), {"cik": 1})
        self.assertIn("CIK0000000001.json", session.get.call_args.args[0])

if __name__ == "__main__":
    unittest.main()
