# MaketData v4.0.0 — MongoDB + SEC EDGAR proof of concept

Collect SEC company identities and historical Company Facts JSON into MongoDB Atlas, with durable checkpoints, idempotent upserts, retries, and safe pacing. **This is a 10-company proof of concept**, not a production-ready 4,900-stock platform. No price provider or calculated ratios yet.

## Setup
1. Create a MongoDB Atlas cluster and database user. Obtain a `mongodb+srv://` connection string. Restrict network access as tightly as your runner setup allows; GitHub-hosted runners have changing egress IPs.
2. Python 3.11+: `pip install -r requirements.txt`
3. Set `MONGODB_URI`, `SEC_USER_AGENT` (real name/company and contact email; required by SEC), and optionally `MONGODB_DATABASE=maketdata`.
4. `python -m src.collect --limit 10` (default); `python -m src.collect --limit 10 --refresh-days 7` for refresh.
5. `python -m unittest discover -s tests -v`

SEC APIs: `https://www.sec.gov/search-filings/edgar-application-programming-interfaces`. Respect SEC fair access; this code uses one request at a time and 0.25s minimum spacing. SEC JSON endpoints may be blocked in some environments; check errors and retry later.

## Storage
- `companies`: one document per CIK, with ticker and name from SEC ticker list.
- `company_facts_raw`: one document per CIK containing SEC Company Facts JSON and metadata; upserted on successful fetch.
- `collection_state`: one document per CIK; records last success, failures, retry schedule.
- `pipeline_runs`: run status and counts.

Raw Company Facts can be large. MongoDB has a 16 MiB BSON document limit; oversized responses are rejected and logged. For a full-universe implementation, **split facts by concept / period** and store raw responses in object storage, with appropriate retention. This POC deliberately avoids silently truncating SEC facts.

## GitHub Actions
Add GitHub repository secrets `MONGODB_URI` and `SEC_USER_AGENT`. Manually run **SEC fundamentals POC** workflow. The scheduled workflow is intentionally disabled until the POC is validated. Never commit secrets.

## Validation checklist
Check counts in MongoDB, compare selected values to original SEC JSON and filings, test rerun idempotency, test transient failure and retry, verify timestamp/filing-date preservation, then expand in phases.

## Changelog
- 2026-11-24 v4.0.0: initial SEC Company Facts + MongoDB Atlas POC, persistent state, tests and manual workflow.

Suggested commit: `feat: initialize MaketData v4 MongoDB SEC ingestion POC`
