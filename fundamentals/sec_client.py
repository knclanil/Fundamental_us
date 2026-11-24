"""SEC API client with explicit identity, pacing and bounded retries."""
import time
import requests

BASE = "https://data.sec.gov"
TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

class SecClient:
    def __init__(self, user_agent, min_interval=0.25, session=None):
        if not user_agent or "@" not in user_agent or "example.com" in user_agent:
            raise ValueError("SEC_USER_AGENT must identify you and include a real contact email")
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate", "Accept": "application/json"})
        self.min_interval = max(0.1, min_interval)
        self.last_call = 0.0

    def get_json(self, url, attempts=4):
        for i in range(attempts):
            elapsed = time.monotonic() - self.last_call
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self.last_call = time.monotonic()
            try:
                response = self.session.get(url, timeout=35)
                if response.status_code in (429, 500, 502, 503, 504):
                    raise requests.HTTPError(f"Retryable HTTP {response.status_code}", response=response)
                response.raise_for_status()
                return response.json()
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError) as exc:
                retryable = not isinstance(exc, requests.HTTPError) or getattr(exc.response, 'status_code', None) in (429, 500, 502, 503, 504)
                if not retryable or i == attempts - 1:
                    raise
                time.sleep(min(2 ** i, 12))

    def tickers(self):
        payload = self.get_json(TICKERS_URL)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected SEC ticker response")
        return sorted(payload.values(), key=lambda row: int(row["cik_str"]))

    def company_facts(self, cik):
        return self.get_json(f"{BASE}/api/xbrl/companyfacts/CIK{int(cik):010d}.json")
