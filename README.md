# MaketData — S&P 500 fundamentals v4.1.4

SEC Company Facts → normalized annual/quarterly fundamentals → MongoDB Atlas.

## Deployment (additive, no data wipe)

1. Back up the MongoDB database before first migration. **Do not drop any collections.**
2. Copy the ZIP's files into the existing repository preserving directory paths. Do not delete unrelated existing files/workflows.
3. Keep existing `MONGODB_URI` and `SEC_USER_AGENT` GitHub Actions secrets.
4. Run **S&P 500 fundamentals v4.1.4** manually with `limit=10`, `refresh_days=0`.
5. Check `MIGRATION_SUMMARY` and `COLLECTION_SUMMARY`. Confirm 10 successes and zero failures before raising the limit.
6. Check annual and quarterly documents for MMM and ACN; confirm fiscal labels, balance metrics, provenance, and uniqueness.

## Index migration behavior

v4.1.3 used a unique `(cik, period_end)` index but left the old unique `(cik, period)` index in place. Both were enforced and SEC updates failed with E11000. v4.1.4 archives and consolidates true same-end duplicates (if any), creates/verifies the new index, and **then** drops only the exact obsolete unique `(cik, period)` index. Unexpected unique indexes fail closed. No automatic age-based deletion. Archived versions are retained in `financial_duplicate_archive`.

## Repo cleanup — safe, review-only

**Keep:** `fundamentals/`, `tests/`, `data/sp500_bootstrap.csv`, `requirements-largecap.txt`, `.github/workflows/largecap-fundamentals.yml`, and existing unrelated pipelines until audited.

**Review before removing:** superseded largecap workflow copies, unused historical POC code, old sample exports, and duplicate documentation. Do not delete legacy collections or workflows without confirming they are unused. The ZIP contains the canonical active S&P 500 pipeline only, not a destructive cleanup script.

## Limits

Tests are local/unit-only; a live Atlas + SEC integration test is still required. Fiscal attribution in SEC Company Facts can vary by issuer and filing; validate source accession and period metadata for representative companies before bulk rollout. The five-year window is applied to newly normalized rows; existing older records are not deleted.
