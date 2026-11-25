# v4.3.2 — SEC balance sheet and coverage corrections
Date: 2026-11-25

- Restrict normalized facts to 10-K and 10-Q, using USD, USD/shares, or shares as appropriate.
- Add NCI, redeemable NCI, combined liabilities/equity, noncurrent liabilities concepts.
- Preserve parent equity separately from equity including NCI.
- Derive missing liabilities from independently reported components where possible; asset-minus-equity remains a **review candidate** because it cannot independently verify reconciliation.
- Add scale-outlier diagnostics and 2% reconciliation threshold.
- Downgrade coverage gaps for spin-offs/partial reporters to informational notes; <16 quarterly records otherwise triggers review.
- Add guarded company-profile cleanup, backup archive, and manual GitHub workflow.

## Caveats
- The six orphan tickers are removed **only from companies**, not financial/state collections; otherwise records could be destroyed without review. Consequently audit may still surface orphan financial records.
- XOM CIK changes in `companies`; existing financial/state records under incorrect CIK are **not** silently reassigned. Review before re-ingestion.
- SEC Company Facts may not expose custom XBRL extension tags. Source verification remains necessary for unreconciled records.
- Existing historical records require recollection/backfill to receive new extracted fields; this release does not automatically overwrite historical financial values.
- The cleanup workflow intentionally does not automatically recollect: the collector's CLI, live constituent list, and CIK matching need confirmation first.
