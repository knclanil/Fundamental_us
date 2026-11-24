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
