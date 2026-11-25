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

### v4.1.7 period-integrity repair
Run the `S&P 500 fundamentals v4.1.7` workflow with `limit=10`, `force_refresh=true`, `refresh_days=0` to overwrite the ten previously refreshed financial records. The collector now replaces each successfully normalized financial document, removing previously stored incorrect cash-flow fields when the SEC source cannot be validated. Check `MMM / FY2026Q3`: any derived cash-flow source must have `current.end=2026-09-30` and `previous.end=2026-06-30`. If valid source observations are unavailable, those fields should be absent, **not zero**. No remote database has been modified by this package.

### v4.1.8 fiscal calendar repair
Run the `S&P 500 fundamentals v4.1.8` workflow with `limit=10`, `force_refresh=true`, `refresh_days=0`. The normalizer now uses actual SEC fact dates and a company fiscal-year calendar inferred from annual 10-K income statement observations. It no longer trusts `fy`/`fp` from a filing to label every comparative fact.

**Existing data repair:** On a successful company refresh, misclassified Q1–Q3 records whose end dates coincide with verified annual records are copied into `financial_period_archive` before removal. Existing legitimate Q4 records are preserved. No MongoDB collections are dropped. Verify AOS no longer has `FY2022Q1` with `period_end=2021-12-31`; verify `FY2021` annual record and `FY2022Q3` quarter. Backup Atlas before running. This is a targeted repair, not a full historical reconciliation of all potentially mislabeled records.

**Limitations:** An annual fiscal-calendar anchor is required; sparse SEC fact payloads may omit some periods. Fiscal year-end changes, nonstandard fiscal quarters, and 52/53-week companies need manual validation. No live SEC or Atlas integration tests were performed.

### v4.1.8.1 test compatibility hotfix
Restores safe fiscal-calendar inference for sparse SEC payloads: 10-K balance-sheet-only observations and Q1 cash-flow-only observations. 10-Q comparative balance-sheet snapshots are never used as calendar anchors. Run the `S&P 500 fundamentals v4.1.8.1` workflow with `limit=10`, `force_refresh=true`, `refresh_days=0` after tests pass.


### v4.1.8.2 targeted diagnostics
Run the S&P 500 fundamentals workflow with `tickers=XOM,HONA,VYLR`, `limit=10`, `force_refresh=true`. Only those exact symbols are examined. If no annual periods are normalized, `DIAGNOSTIC` logs show counts of SEC 10-K observations, fiscal calendar mismatches, out-of-window facts and duration mismatches. No SEC raw JSON is logged. The collector continues to protect existing financial records when no annual rows are available. The job exits nonzero if any requested company fails; inspect the diagnostic lines rather than refreshing all 500.


### v4.1.8.3: Diagnose missing annual periods
In GitHub Actions select **S&P 500 fundamentals v4.1.8.3**, set `tickers=XOM,HONA,VYLR`, `limit=10`, and `force_refresh=true`. Review `SEC_INVENTORY`, `DIAGNOSTIC`, and `FAILED` lines. `SEC_INVENTORY` prints only for explicitly targeted ticker runs and does not write source payloads to the database. The three tickers may still fail: this release gathers evidence, not a speculative data fix.


### v4.1.8.4 — Partial SEC filing history
A company with verified 10-Q quarterly periods but no 10-K annual periods is now
reported as `PARTIAL` and its quarterly data is stored. No annual records are
constructed from 10-Q filings. If no periods normalize, the company is reported
`INSUFFICIENT_DATA`, existing financial data is preserved, and a retry cooldown
is applied. Coverage status (`reporting_status`, `annual_period_count`,
`quarterly_period_count`) is stored in `largecap_collection_state`.

To verify the three recent quarterly-only companies, dispatch the workflow with
`tickers=XOM,HONA,VYLR`, `limit=10`, `force_refresh=true`. A successful run
may report `partial=3`, not `success=3`. This does **not** establish five years
of historical annual data for the three CIKs.

## v4.2.0 — Financial Data Quality Audit (read-only)

Open **Actions → Financial data quality audit v4.2.0 → Run workflow**. The separate audit workflow reads `MONGODB_URI` and the `maketdata` database and uploads the `maketdata-financial-quality-v4.2.0` artifact containing:

- `quality_report.json` — full company-level diagnostics and aggregate totals.
- `company_coverage.csv` — period counts, most recent period, and missing-metric counts.
- `quality_issues.csv` — flagged records for investigation.

The workflow also runs Mondays at 06:45 UTC. To run locally after installing `requirements-largecap.txt`, set `MONGODB_URI` and execute `python -m fundamentals.quality_audit --output artifacts/financial-quality`.

**Scope and interpretation:** This is a *database* audit, not a comparison with fresh SEC source data or a point-in-time S&P 500 constituent list. Five annual and twenty quarterly periods are coverage targets, not universal guarantees. Balance-sheet residuals are flags, not proof of accounting errors; noncontrolling interests and alternate equity tags can explain them. Missing values are counted across existing stored documents; zero is a valid present value. This audit does not edit MongoDB or change the existing v4.1.8.4 collection workflow.


## v4.2.1 financial audit corrections (2026-11-25)
- Reads financial metrics from `metrics` nested document, not top-level fields. Zero counts as present.
- Balance sheet checks now read the same nested metrics. Discrepancies are review flags only.
- A company with 19 quarters is not automatically flagged. Under 16 quarters is a review trigger, not proof of a defect.
- `universe_class` distinguishes historical collector-state CIKs from legacy/orphan records. Neither is independently verified current S&P 500 membership.
- The collector and MongoDB documents are unchanged. The audit is read-only.
- Run **Financial data quality audit v4.2.1** and download its artifact.
