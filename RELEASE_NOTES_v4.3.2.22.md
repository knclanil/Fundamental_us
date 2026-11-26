# MaketData v4.3.2.22 — Initial Remediation (Partial)

## Implemented
- Annual extraction now considers an extra year of source observations before retaining the most recent five fiscal years. This fixes the rolling-calendar-cutoff class of missing fifth annual period. Does not establish whether Agilent has five eligible annual SEC periods; live validation is required.
- Single-accession balance-sheet alignment may now populate a missing assets/liabilities/equity component when a complete compatible accession reconciles within the existing 2% threshold. Existing reconciled rows remain unchanged. SEC Company Facts does not expose full XBRL context dimensions, so this remains a conservative heuristic, not independent validation of accounting correctness.
- Added regression tests for fiscal lookback and missing-component alignment.

## Tests
- 10 targeted tests passed (fact alignment, normalization, new regression tests).
- Full test collection blocked: pymongo is not installed in the execution environment (16 collection errors).
- No live SEC or MongoDB integration test executed. No claim of actual reduction in audit issues.

## Unresolved
- Most reconciliation cases, XBRL taxonomy/sector mappings, incomplete quarterly histories, collection status, universe differences, scheduled workflow failures, identity mismatches, and broader database repairs are NOT fixed in this release.
- Run a dry-run and target A first; back up MongoDB and inspect new quality audit before broader refresh.
