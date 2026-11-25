# v4.3.2.3 — Verified XOM SEC issuer resolution (2026-11-25)

- SEC feed XOM maps to 0002115436; explicitly resolve to parent issuer 0000034088.
- Sync records override evidence in `resolved_overrides` rather than failing the run.
- Collector uses the same verified resolver before requesting companyfacts.
- Recollection can run after a successful dry-run sync (`recollect=true`, `apply_sync=false`).
- Avoid duplicate company profiles when a ticker already has a profile with a non-CIK `_id`.
- Financial historical data is not migrated or deleted by this release.

## Safe rollout
1. Set `apply_sync=false`, `recollect=false` for dry run; expect 499 unchanged, XOM in `resolved_overrides`, no unresolved conflicts.
2. Set `apply_sync=true`, `recollect=false` to update XOM only (verify summary).
3. Set `apply_sync=false`, `recollect=true`, `tickers=XOM` to test 10-K/10-Q collection.
4. Inspect 10-K observations, annual periods, CIK and MongoDB records before full universe collection.

**Important:** SEC ticker JSON is not a definitive source of historical issuer continuity. This override is an explicit project-specific identity decision and must be reverified if SEC mappings change.
