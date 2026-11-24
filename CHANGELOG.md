# Changelog

## 4.1.2 — 2026-11-24
- Use SEC fiscal-year (`fy`) and fiscal-period (`fp`) labels instead of `CY` frames.
- Include balance-sheet point-in-time metrics with source accession/form/filing metadata.
- Reject cumulative YTD amounts when labeling standalone quarterly flows.
- Match existing records by CIK + period_end; preserve earlier collections and raw POC data.
- Add regression tests for non-December fiscal year, balance sheet and quarterly periods.
- No automated deletion of existing financial data.
