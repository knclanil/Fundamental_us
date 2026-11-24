# MaketData v4.1.2 — Fiscal-period and balance-sheet fix

This is a **drop-in update** to v4.1.1, not a replacement for the old v4.0.3 POC.

## Install
Copy the included `fundamentals/`, `tests/test_largecap.py`, and `.github/workflows/largecap-fundamentals.yml` into the repository. Keep existing secrets `MONGODB_URI`, `SEC_USER_AGENT` and old collections.

Run GitHub Actions **S&P 500 fundamentals v4.1.2** with `limit=10`, `refresh_days=0` to refresh the first ten companies even if collected recently. Then inspect `financial_annual` for `ACN`, `period_end=2026-08-31` and `period=FY2026`. Verify `metric_sources` and available balance sheet fields.

## Data quality caveats
- SEC Company Facts `fy`/`fp` represent filing metadata, not a perfect standalone fiscal-period identifier for every amended/restated filing. Each stored metric includes its own SEC source details. Compare against original filings for critical decisions.
- Quarterly flows are only stored when the SEC supplies a standalone 70–110 day value; YTD 6/9 month figures are not treated as quarterly. Q4 is not automatically synthesized. Quarterly coverage may therefore be incomplete.
- Balance sheet items use SEC instant facts and are matched to annual/quarterly reporting dates. Fields missing from SEC facts remain absent.
- Financial period keys use `cik` and `period_end`; old unique indexes on `cik,period` may remain but no data is deleted. A future migration can safely rebuild indexes after auditing historical data.
- Existing legacy `CY...` records are updated only for companies and dates reprocessed. Run a staged backfill to migrate all companies.
- `--min-market-cap` is retained for CLI compatibility, but S&P 500 universe is a proxy, not actual $10B filtering.
- Five-year cutoff applies to new normalization, but older existing records are **not yet pruned**. Do not assume database retention has been enforced.

## Validation
`python -m unittest discover -s tests -p test_largecap.py -v`

Commit: `fix(v4.1.2): correct SEC fiscal labels, balance sheet facts and quarterly flows`
