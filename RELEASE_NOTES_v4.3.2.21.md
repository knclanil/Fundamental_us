# v4.3.2.21 — Conservative balance-sheet SEC fact alignment

- When a normalized balance sheet is unreconciled, try coherent SEC Company Facts instant observations from the **same accession and reporting end date** and the matching filing form (10-K annual / 10-Q quarterly).
- Accept replacement only when the coherent filing reconciles to within 2% of assets and improves the original difference. Never fabricate or numerically adjust a fact.
- Preserve SEC tag, accession, filed date, and a per-period alignment diagnostic.
- Existing 404 handling and collection checkpoint behavior remain unchanged.

## Safe targeted repair
Use GitHub Actions **SEC Fundamentals (Manual)** with `universe=tickers`, `tickers=A` (or another affected ticker), `limit=1`, `force_refresh=true`. Inspect the audit before expanding to more tickers. This writes the selected company's financial rows, so back up MongoDB first. The collector retains historical fields missing from new SEC output; consequently some old values may remain and require separate review.

## Limitations
This is a conservative source-selection fix, not a guarantee that all 2,964 historical reconciliation issues disappear. Company Facts lacks complete context dimensions, and not every issuer has a reconciled same-accession combination. No live SEC or MongoDB validation was run here.
