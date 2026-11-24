"""v3.2.1 (2026-11-24): free-tier quota and cache tests."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from alpha_vantage import enrich_caps
from priority import cap_lookup

class Response:
    def raise_for_status(self): pass
    def json(self): return {'MarketCapitalization': '250000000000'}
class Session:
    def __init__(self): self.calls = []
    def get(self, url, params, timeout):
        self.calls.append(params['symbol'])
        return Response()

def test_quota_and_cache(tmp_path, monkeypatch):
    monkeypatch.setenv('ALPHA_VANTAGE_API_KEY', 'test-only-secret')
    cache = tmp_path / 'caps.json'
    quota = tmp_path / 'quota.json'
    session = Session()
    enrich_caps(['AAA', 'BBB'], cache, quota, daily_limit=1, session=session, delay=0,
                now=datetime(2026, 11, 24, tzinfo=timezone.utc))
    assert session.calls == ['AAA']
    assert json.loads(quota.read_text())['requests_used'] == 1
    assert cap_lookup(tmp_path / 'missing.parquet', alpha_cache_path=cache)['AAA'] == 250000000000
    enrich_caps(['AAA', 'BBB'], cache, quota, daily_limit=1, session=session, delay=0,
                now=datetime(2026, 11, 24, tzinfo=timezone.utc))
    assert session.calls == ['AAA']
