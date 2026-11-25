# MaketData v4.3.1 — Automated Financial Repair Validation

This release adds a **fail-closed validation gate** to the v4.3.0 repair workflow.

- Validate candidate fiscal-year/quarter/end-date identity and finite numeric values.
- Validate Q4 additive derivation source tags, durations, chronology, and filing accession references.
- Validate fiscal year-end balance sheet snapshots and accession references.
- Check balance sheet consistency **after applying all proposed additions together**, rather than one field at a time.
- Label every candidate `VALIDATED`, `REVIEW`, or `FAIL` in dry-run; only `VALIDATED` candidates can become `WRITTEN` when `apply=true`.
- Preserve existing non-null values; new financial periods are still not inserted.
- Replace old v4.3.0 repair workflow with v4.3.1 to avoid accidental use of the less restrictive version.

**Limitations:** A `VALIDATED` result means automated consistency and provenance-structure checks passed. It is **not independent confirmation of the SEC filing value**. Existing non-null incorrect values and unsupported industry-specific facts are not auto-corrected. This release does not independently prove all 19,707 candidates are safe.

## Run

1. GitHub Actions → **Financial repair validation v4.3.1** → `tickers=ALL`, `apply=false`.
2. Download `financial-repair-v4.3.1` artifact. Check counts for `validated`, `review`, `fail`, and errors.
3. Only after review, rerun with `apply=true`. This applies validated missing fields only.
4. Rerun the read-only financial quality audit and compare with baseline.

Suggested commit: `feat(v4.3.1): validate SEC repair candidates before guarded MongoDB writes`
