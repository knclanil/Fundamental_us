# v4.3.2.5 — Consolidated identity and financial integrity

- Normalize numeric and zero-padded SEC CIKs **only in the read-only audit**. No database migrations or deletions.
- Join company profiles, collector state and annual/quarterly documents by normalized CIK.
- Detect profile collisions and unmatched records; export `identity_review.csv`.
- Recompute coverage, missing-metric and balance-sheet discrepancy reports by canonical issuer.
- Add a single workflow with before/after audits and optional existing guarded SEC repair.
- Repair is OFF by default; `run_repair=true, apply_repair=false` is dry-run; writes require explicit `apply_repair=true`.
- No blind repair of 442 unreconciled balance sheets: SEC fact provenance is required.
- Do not use ALL repair until reviewing pilot output.

Suggested commit: `feat(v4.3.2.5): reconcile CIK identities and consolidate financial integrity audit`
