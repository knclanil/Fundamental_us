# MaketData v4.1.3 — S&P 500 Fundamentals

This is a drop-in update of v4.1.2, fixing the `E11000 duplicate key` failure when adding a unique index to pre-existing financial collections.

## Installation
Copy the package contents into your existing MaketData repository, retaining the relative paths. Do not delete existing MongoDB collections. Commit and run **S&P 500 fundamentals v4.1.3** with `limit=10`, `refresh_days=0` to force a refresh of the first ten tickers.

## Migration safety
On startup, the pipeline groups existing records by `(cik, period_end)` in `financial_annual` and `financial_quarterly`. For duplicate groups it picks the record with the most populated metrics as the canonical record, merges missing metric fields, archives **each removed original document** in `financial_duplicate_archive`, verifies the archive copy exists, and only then removes the extra originals. Conflicting values are retained in the archived documents. It creates the unique indexes after the duplicate groups have been reconciled. The migration is designed to be safe to rerun.

**Important:** This migration intentionally consolidates documents with the same CIK and end date. If records represent different durations or fiscal contexts, their originals remain in the archive, but a later schema update should use a more expressive period identity. It does not independently validate the accuracy of the SEC normalization.

## Secrets
`MONGODB_URI` and `SEC_USER_AGENT` in GitHub Actions; `MONGODB_DATABASE` defaults to `maketdata`.

## Validate
Inspect the `MIGRATION_SUMMARY` and `COLLECTION_SUMMARY` logs, then verify `financial_annual`, `financial_quarterly`, and `financial_duplicate_archive` in MongoDB Atlas. Do not delete the archive until you have audited it. The archive temporarily uses additional free-tier storage.

## Suggested commit
`fix(v4.1.3): archive and reconcile duplicate financial periods before indexing`
