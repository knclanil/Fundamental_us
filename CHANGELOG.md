# v4.0.3 — 2026-11-24
- Normalize timezone-naive MongoDB UTC timestamps before refresh and retry comparisons.
- Enable timezone-aware MongoDB datetime decoding.
- Run only v4 SEC POC tests; do not import legacy v3 tests.
- Install POC dependencies from a separate file so the existing root requirements can remain unchanged.
- Add four datetime regression tests.

Commit: `fix(v4.0.3): handle MongoDB UTC timestamps and isolate SEC POC tests`
