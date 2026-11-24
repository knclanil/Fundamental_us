# MaketData — S&P 500 fundamentals v4.1.5

SEC Company Facts → normalized annual/quarterly fundamentals → MongoDB Atlas.

## Deployment (additive, no data wipe)

1. Back up the MongoDB database before first migration. **Do not drop any collections.**
2. Copy the ZIP's files into the existing repository preserving directory paths. Do not delete unrelated existing files/workflows.
3. Keep existing `MONGODB_URI` and `SEC_USER_AGENT` GitHub Actions secrets.
4. Run **S&P 500 fundamentals v4.1.5** manually with `limit=10`, `refresh_days=0`.
5. Check `MIGRATION_SUMMARY` and `COLLECTION_SUMMARY`. Confirm 10 successes and zero failures before raising the limit.
6. Check annual and quarterly documents for MMM and ACN; confirm fiscal labels, balance metrics, provenance, and uniqueness.

## Index migration behavior

v4.1.3 used a unique `(cik, period_end)` index but left the old unique `(cik, period)` index in place. Both were enforced and SEC updates failed with E11000. v4.1.5 archives and consolidates true same-end duplicates (if any), creates/verifies the new index, and **then** drops only the exact obsolete unique `(cik, period)` index. Unexpected unique indexes fail closed. No automatic age-based deletion. Archived versions are retained in `financial_duplicate_archive`.

## Repo cleanup — safe, review-only

**Keep:** `fundamentals/`, `tests/`, `data/sp500_bootstrap.csv`, `requirements-largecap.txt`, `.github/workflows/largecap-fundamentals.yml`, and existing unrelated pipelines until audited.

**Review before removing:** superseded largecap workflow copies, unused historical POC code, old sample exports, and duplicate documentation. Do not delete legacy collections or workflows without confirming they are unused. The ZIP contains the canonical active S&P 500 pipeline only, not a destructive cleanup script.

## Limits

Tests are local/unit-only; a live Atlas + SEC integration test is still required. Fiscal attribution in SEC Company Facts can vary by issuer and filing; validate source accession and period metadata for representative companies before bulk rollout. The five-year window is applied to newly normalized rows; existing older records are not deleted.

## Force refresh (v4.1.5)
The previous v4.1.4 runs skipped all 10 companies even with refresh_days=0 because
`next_retry_at` is checked before the last-success timestamp. `refresh_days=0`
is **not** an override for retry backoff. The explicit `force_refresh=true` input
bypasses both checks. To validate the data path, manually run limit=10,
force_refresh=true, refresh_days=7. Verify success=10 and failed=0.
Normal scheduled runs leave force_refresh=false.

## Repository inventory / cleanup policy
The uploaded repository also contains historical pipelines in `src/`,
`v4_mongodb/`, and workflows `collect.yml`, `sec-poc.yml`, and
`sec-mongodb-v4.yml`, along with tracked Parquet data and state.
These may still power separate features. No legacy files or data were deleted
without proof of non-use. Disable obsolete workflows in GitHub only after
confirming ownership and last run; avoid deleting any MongoDB collections.


### v4.1.6 quarterly cash flow
Q2 = 6-month YTD minus Q1; Q3 = 9-month YTD minus 6-month YTD; Q4 = annual minus 9-month YTD, where matching fiscal-year sources exist. Derived fields include `metric_sources.<metric>.method` and source components. Missing source periods remain missing. Q4 may contain only cash-flow metrics. Force-refresh the first 10 companies and validate individual filings before scaling. No existing MongoDB records are deleted.
