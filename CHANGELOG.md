## v4.3.2.14 — 2026-11-25
- Added automatic BlackRock ETF holdings refresh with validated snapshot fallback.
- Added non-destructive MongoDB company-profile synchronization, issuer identity guards, and resumable SEC financial collection batches.
- Added optional strict $10B market-cap intersection using verified CSV.
- Added GitHub Actions automation and deployment/verification guide.
- No live MongoDB deployment or automatic market-cap provider included.

## v4.3.1 — 2026-11-25
- Add automated SEC provenance and accounting validation gate for financial repair candidates.
- Allow writes only for PASS candidates, and report REVIEW/FAIL without modifying MongoDB.
- Replace v4.3.0 workflow with v4.3.1, add validation regression tests.

## v4.2.2 — 2026-11-25
- Derive Q4 additive income-statement metrics from annual minus three standalone fiscal quarters only when source tags and period boundaries match.
- Populate Q4 year-end balance-sheet instant values with source metadata; leave EPS unestimated.
- Add opt-in, dry-run-first MongoDB historical backfill and manual GitHub Actions workflow.
- Add regression tests; preserve existing Q4 cash-flow behavior and other repository contents.
- Suggested commit: `feat(v4.2.2): complete source-validated Q4 statements with guarded backfill`

## v4.2.1 — 2026-11-25
- Correct nested financial metric mapping in read-only quality audit.
- Avoid 19-quarter false positives; separate historical collector coverage from legacy records.
- Add audit regression tests and update workflow version.

## v4.1.8.4 — 2026-11-25
- Support quarterly-only SEC Company Facts without inventing annual records.
- Persist verified 10-Q quarterly rows when no 10-K annual rows exist.
- Classify runs as success, partial, or insufficient_data; preserve old data on empty source.
- Record coverage status and period counts in largecap_collection_state.
- Preserve existing annual data and do not prune historical quarterly rows on partial collection.
- Add quarterly-only regression tests and workflow test step.

## v4.1.8.2 — 2026-11-25
- Add optional exact-ticker targeted collection without rewriting other companies.
- Add aggregated SEC annual normalization diagnostics when no annual records are produced.
- Preserve no-annual safeguard, prior data, and cooldown logic; force refresh remains opt-in.
- Add diagnostic regression tests and workflow dispatch input.

## v4.1.6 — Quarterly cash-flow normalization (2026-11-24)
- Derive standalone Q2 and Q3 operating cash flow/capex by subtracting compatible fiscal-year-to-date values.
- Derive Q4 cash flow/capex as annual minus Q3 YTD when both are available.
- Mark derived metric provenance; compute free cash flow from standalone operating cash flow and capex.
- Never treat cumulative YTD as standalone. Leave unavailable values missing.
- Preserve all other repository files and MongoDB collections; no destructive migration.
- Added focused regression tests. Live SEC/Atlas integration not performed locally.

## v4.1.5 — 2026-11-24
- Add explicit force-refresh workflow input and CLI flag.
- Bypass both success-age and retry-backoff gates when forced.
- Log effective runtime configuration; add six regression tests.
- Run migration index and refresh tests in GitHub Actions.
- Document non-destructive repository cleanup inventory.

# Changelog

## v4.1.4 — 2026-11-24
- Fixed E11000 caused by conflicting unique `(cik, period)` and `(cik, period_end)` indexes.
- Index migration now creates the replacement before dropping the precisely matched obsolete index.
- Fail-closed checks for unexpected unique indexes and ambiguous duplicate identities.
- Archive all versions of reconciled duplicates before mutation; no automatic collection deletion.
- Added regression tests for index replacement ordering and rollback-on-failure behavior.
- Retained SEC fiscal-year, balance-sheet, filing-source, and quarterly normalization changes.
- Added non-destructive repository cleanup guidance.

Suggested commit: `fix(v4.1.4): reconcile legacy unique indexes and harden SEC collection`

## v4.1.7 — 2026-11-24
- Anchor Q2/Q3 cash-flow YTD inputs to actual quarter reporting end dates, not SEC filing `fy`/`fp` labels.
- Require a corresponding income-statement quarter and a matching prior quarter to prevent comparative prior-year cash flow from contaminating current-year records.
- Require matching fiscal-year starts and exact previous/current period ends.
- Replace financial documents on successful refresh so invalid stale cash-flow metrics and provenance are removed (rather than retained by `$set`).
- Add three regression tests for comparative-year mismatch, correct current-year Q3, and mismatched fiscal starts.
- No MongoDB collections are dropped; force-refresh is needed to repair previously saved documents.

## v4.1.8 — 2026-11-24
- Infer fiscal quarters and fiscal years from actual reporting end dates and the latest verified 10-K annual reporting calendar.
- Reject prior-year balance-sheet snapshots in 10-Q filings when they coincide with fiscal year-end; retain legitimate annual 10-K snapshots.
- Preserve original SEC filing fy/fp as `filing_fy`/`filing_fp` in metric provenance.
- Archive and remove legacy Q1-Q3 quarterly documents at verified annual period ends after successful refresh.
- Add calendar-year, August-year-end, and comparative-filing regression tests.
- Limitation: material fiscal-year-end changes and unusual 52/53-week calendars require additional review.

## v4.1.8.1 — 2026-11-25
- Fix two pre-collection GitHub Actions test failures caused by requiring income-statement facts for fiscal-calendar inference.
- Add safe 10-K instant-only fallback and Q1 cash-flow-only fallback when annual income-statement observations are absent.
- Do not use comparative 10-Q balance-sheet instants as fiscal calendar anchors.
- Add three sparse-payload regression tests.
- No MongoDB migration or destructive changes added.

## v4.1.8.3 — 2026-11-25
- Added read-only SEC_INVENTORY before normalization on explicitly targeted runs.
- Logs mapped CIK, SEC entity name, namespace/tag inventory, 10-K counts, candidate end dates and recognized metrics.
- Preserved normalization, MongoDB write safeguards, and existing scheduling defaults.
- Added inventory unit tests.

## v4.2.0 — 2026-11-25
- Added a separate, read-only MongoDB financial quality audit; collector v4.1.8.4 is unchanged.
- Reports annual/quarterly coverage, missing metrics, fiscal-label issues, duplicate identities, balance-sheet residuals, and YTD cash-flow source date mismatches.
- Added downloadable JSON and CSV GitHub Actions artifacts, a weekly schedule, and focused regression tests.
- Does not alter MongoDB documents or attempt automatic accounting corrections.

## 4.3.2.13 — 2026-11-25
- Added BlackRock IWB/IWM/IWV holdings CSV downloader and schema-aware parser.
- Added validated ETF holdings snapshot and GitHub Actions artifact refresh workflow.
- Added `blackrock_holdings` SEC universe option, separate from strict $10B+ universe.
- Added offline parsing tests using user-provided Nov 24, 2026 holdings files.
- No automatic market-cap inference, MongoDB deletion, or deployment.
