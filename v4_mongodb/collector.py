import sys
import types
import unittest

from datetime import timedelta
from unittest.mock import patch


# ---------------------------------------------------------
# Mock SEC EDGAR API for offline unit tests
# ---------------------------------------------------------
# sec-edgar-api 1.1.0 currently fails during import because
# of an incompatibility with pyrate-limiter.
#
# These tests only validate collector helper functions.
# They do not require a live SEC API connection.
# ---------------------------------------------------------

mock_sec_edgar_api = types.ModuleType("sec_edgar_api")


class MockEdgarClient:
    def __init__(self, *args, **kwargs):
        pass


mock_sec_edgar_api.EdgarClient = MockEdgarClient


# Import collector with the SEC dependency temporarily mocked.
# Restore sys.modules afterward to avoid affecting other tests.

with patch.dict(sys.modules, {"sec_edgar_api": mock_sec_edgar_api}):
    from v4_mongodb.collector import (
        flatten_facts,
        is_due,
        parse_universe,
        now,
    )


# ---------------------------------------------------------
# Collector Unit Tests
# ---------------------------------------------------------

class CollectorTests(unittest.TestCase):

    def test_parse_universe(self):
        data = {
            "fields": [
                "cik",
                "name",
                "ticker",
                "exchange",
            ],
            "data": [
                [
                    320193,
                    "Apple Inc.",
                    "AAPL",
                    "Nasdaq",
                ]
            ],
        }

        result = parse_universe(data)

        self.assertEqual(result[0]["ticker"], "AAPL")

    def test_flatten_facts(self):
        raw = {
            "facts": {
                "us-gaap": {
                    "Assets": {
                        "label": "Assets",
                        "units": {
                            "USD": [
                                {
                                    "val": 12
                                }
                            ]
                        },
                    }
                }
            }
        }

        docs = list(flatten_facts(raw, 320193))

        self.assertEqual(
            docs[0]["_id"],
            "320193:us-gaap:Assets:USD",
        )

        self.assertEqual(
            docs[0]["observations"][0]["val"],
            12,
        )

    def test_due_new(self):
        self.assertTrue(
            is_due(None, 7)
        )

    def test_due_recent(self):
        self.assertFalse(
            is_due(
                {
                    "last_success_at": now()
                },
                7,
            )
        )

    def test_due_old(self):
        self.assertTrue(
            is_due(
                {
                    "last_success_at": now()
                    - timedelta(days=9)
                },
                7,
            )
        )

    def test_retry_cooldown(self):
        self.assertFalse(
            is_due(
                {
                    "next_retry_at": now()
                    + timedelta(hours=1)
                },
                0,
            )
        )


if __name__ == "__main__":
    unittest.main()
