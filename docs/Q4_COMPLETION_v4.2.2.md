# v4.2.2 Q4 financial statement completion

## Scope
- Normalizer fills Q4 revenue, gross profit, operating income and net income only when annual and all three standalone quarters have compatible SEC metric tags, dates and sources.
- Copies fiscal-year-end balance-sheet instant values from the annual record, preserving provenance.
- Does **not** derive EPS (nonadditive denominators); it remains missing unless independently reported.
- Preserves existing Q4 operating cash flow, capex and free cash flow logic.
- Q4 historical backfill is independent, defaults to **dry-run**, and uses atomic per-field conditional `$set` (no document replacement or deletion).
- Does not fetch new SEC facts for the historical backfill. Missing/incompatible source evidence results in no change.

## Run in GitHub Actions
1. Deploy this **full repository** to the existing GitHub repository; preserve repository secrets.
2. Open Actions → **Q4 financial completion v4.2.2** → Run workflow.
3. Set `tickers=AAPL`, `apply=false`; inspect `DRY_RUN` and `Q4_COMPLETION_SUMMARY` logs.
4. If correct, rerun `tickers=AAPL`, `apply=true`; verify AAPL Q4 records and rerun the quality audit.
5. Expand to a small ticker batch, then `ALL` only after validation. `ALL` uses a max of 500 companies by default.
6. The regular fundamentals collector now generates completed Q4 values for future refreshes; it is not automatically force-refreshed by this workflow.

## Local commands
`python -m unittest discover -s tests -p 'test_q4_completion_v422.py' -v`

`python -m fundamentals.q4_backfill --tickers AAPL` (dry-run)

`python -m fundamentals.q4_backfill --tickers AAPL --apply` (guarded write)

## Known limitations
- EPS is intentionally not derived; a future SEC-aware EPS validation enhancement is needed.
- Income metrics require source tags to agree across all quarters and annual period; legitimate tag changes are conservatively skipped.
- This version does not automatically reconcile restatements across filing dates, though it retains filing metadata for review.
- Backfill only updates **existing Q4** documents and requires all Q1-Q3 and annual source records.
- The regular collector still uses document replacement on explicit refresh; backfill itself never replaces records.
- No live SEC or MongoDB Atlas test was performed in the build environment.

Suggested commit: `feat(v4.2.2): complete source-validated Q4 statements with guarded backfill`
