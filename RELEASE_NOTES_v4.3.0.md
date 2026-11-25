# MaketData v4.3.0 — Consolidated Guarded Financial Repair

Release date: 2026-11-25. Suggested commit: `feat(v4.3.0): add guarded SEC financial repair and preserve backfills`

## Scope implemented
- SEC Company Facts re-normalization using existing validated fiscal/Q4 logic.
- Missing-field detection and source-traceable candidate generation for existing annual and quarterly records.
- Dry-run default; opt-in atomic writes only for missing fields, preserving existing values and provenance.
- Explicit conflict reporting, balance-sheet insertion guard, and no fabricated EPS.
- Scheduled collector now preserves existing non-null fields absent from a new SEC normalization.
- Downloadable CSV and JSON repair reports; GitHub Actions manual workflow.

## Important limitations
- Existing incorrect non-null metrics and 441 reconciliation findings are **not automatically corrected**. They require SEC source verification.
- Does not add industry-specific extension XBRL tags or new reporting periods automatically.
- Does not independently verify all SEC financial values; does not guarantee all missing fields recoverable.
- A normal collector refresh may replace a non-null value with a different newly extracted non-null SEC value; review conflicts.
- Does not execute against MongoDB from this build environment.

## Runbook
1. Replace repository files with this full repository ZIP, preserving GitHub secrets.
2. Actions → Financial repair and validation v4.3.0 → Run workflow → `tickers=AAPL`, `apply=false`.
3. Download the `financial-repair-v4.3.0` artifact and inspect `repair_details.csv` and `repair_summary.json`.
4. Run `tickers=ALL`, `apply=false` and review conflicts and `BALANCE_REVIEW` rows.
5. Only after review, run `tickers=ALL`, `apply=true` for guarded missing-field additions.
6. Run the existing Financial Quality Audit workflow and compare with baseline audit.

## Database safety
No deletes, no blanket replacement by repair job, no modifications in dry-run. Only absent fields in existing records are eligible for writes. The collector's original ReplaceOne path is retained with missing-field preservation. Use GitHub Actions concurrency to prevent overlap with collector workflow.
