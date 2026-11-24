# Changelog

## v4.1.3 — 2026-11-24
- Added idempotent duplicate-period migration before unique index creation.
- Archived original duplicate documents in `financial_duplicate_archive` before deletion.
- Merged nonconflicting metric fields into the preferred document; conflicting values remain in archived originals.
- Added migration summary and unit tests. Existing SEC collection, fiscal normalizer and five-year scope retained.
- **Caveat:** records sharing a period end but representing genuinely different reporting durations require future schema refinement; archived originals are retained for audit.
