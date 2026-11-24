# Changelog

## v4.1.0 — 2026-11-24
- Added market-cap-filtered large-cap universe (>= USD 10B) from best-effort Nasdaq screener feed.
- Added SEC CIK mapping and 5-year normalized annual/quarterly MongoDB storage.
- Added UTC-aware incremental scheduling, retries, per-company logging, and unit tests.
- Added separate GitHub Actions workflow; preserved v4.0.3 source and raw data.

Suggested commit: `feat(v4.1.0): add five-year large-cap SEC fundamentals collector`
