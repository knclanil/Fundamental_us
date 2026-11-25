# v4.3.2.9 — Conservative production-normalizer EPS fallback

## Scope
- Integrates a narrowly scoped, review-flagged Basic/Diluted EPS fallback into `fundamentals/normalize.py`, the **actual collector's** normalization function.
- Only derives EPS when continuing and discontinued EPS facts both exist, share the same accession, period start/end, form, unit, and match a valid annual or discrete Q1–Q3 period. Direct reported EPS wins. Missing discontinued EPS is NOT assumed zero.
- Rejects facts that explicitly carry `segment` or `dimensions` metadata. **SEC Company Facts does not expose full context dimensions**; missing metadata does NOT verify that an observation is dimensionless.
- Leaves reported liabilities intact, avoids automatic scale correction and avoids unverified historical overwrites.
- Adds 6 new regression tests and wires them into the existing main-branch collector workflow.

## Known limitations
- This is **not** a verified fix for the 443 balance issues, 4,107 conflicts, or 4,803 EPS source reviews. It may improve a subset of EPS gaps; no live SEC/MongoDB integration or full-universe post-run audit was performed.
- Existing SEC Company Facts equity context ambiguity cannot be solved by filtering missing `segment` metadata. Filing-level XBRL context verification is still required before replacing questionable equity values.
- Derived EPS is flagged `review_required=True`; the normalizer can output it, and the collector can persist it on refresh. Treat it as review-only in downstream analysis until verified.
- `force_refresh=true` triggers real MongoDB writes via `ReplaceOne`. **Do not use force refresh on production data solely to validate this release.** First run local tests, inspect a dry-run/backup, and establish a rollback path.

## Verification
`python -m unittest discover -s tests -p 'test_normalization_v4329.py' -v`

## Commit message
`fix(v4.3.2.9): add conservative EPS fallback to production normalizer`
