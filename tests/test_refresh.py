"""v4.1.5 refresh semantics regression tests."""
import unittest
from datetime import datetime, timedelta, timezone
from fundamentals.collect import due

class RefreshTests(unittest.TestCase):
    def test_recent_success_skipped_normally(self):
        self.assertFalse(due({'last_success_at': datetime.now(timezone.utc)}, 7))
    def test_force_overrides_recent_success(self):
        self.assertTrue(due({'last_success_at': datetime.now(timezone.utc)}, 7, True))
    def test_force_overrides_retry_backoff(self):
        state={'last_success_at': datetime.now(timezone.utc), 'next_retry_at': datetime.now(timezone.utc)+timedelta(days=2)}
        self.assertFalse(due(state, 0))
        self.assertTrue(due(state, 0, True))
    def test_zero_interval_not_force_with_retry(self):
        self.assertFalse(due({'next_retry_at': datetime.now(timezone.utc)+timedelta(hours=1)}, 0))
    def test_zero_interval_refreshes_success(self):
        self.assertTrue(due({'last_success_at': datetime.now(timezone.utc)-timedelta(seconds=2)}, 0))
    def test_new_company_due(self):
        self.assertTrue(due(None, 7))

if __name__ == '__main__': unittest.main()
