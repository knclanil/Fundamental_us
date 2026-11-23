# US Stock Market Research Pipeline — v2.0.0

**Status: implementation scaffold, NOT live-validated production ingestion.**

## Scope
- Daily dynamic exchange symbol discovery (NASDAQ Trader directories), de-duplication, additions and inactive marking.
- Company metadata with best-effort sector and industry extraction.
- StockAnalysis `/statistics/`, `/financials/`, `/financials/balance-sheet/`, `/financials/cash-flow-statement/`, `/financials/ratios/` HTML table extraction.
- Compressed Parquet data, GitHub Actions scheduler, per-page failure logs, no deletion of financial history.
- Market OHLCV is a **future extension**; no authorized daily-price provider has been selected. `collect_prices` is reserved but does not currently trigger collection.

## Setup
1. Create a private GitHub repository and upload the contents of this folder.
2. Install: `pip install -r requirements.txt`.
3. Test: `pytest -q` and `python src/pipeline.py --dry-run`.
4. Review the websites' terms and robots.txt; obtain permission where required. **Do not enable collection unless authorized.**
5. Set your contact email in `config/settings.json` and change `allow_automated_collection` to `true` only when authorized.
6. Start with `universe: custom`, `max_tickers: 3` and validate actual page parsing against source output.
7. Use `universe: exchange` to discover exchange-listed symbols, with filtering caveats below. Set `max_tickers: 0` to disable the cap.
8. In GitHub Actions, enable workflows and run `Collect market fundamentals` manually. Scheduled runs occur Tue–Sat 03:15 UTC.

## Files
- `data/dimensions/instruments.parquet`: ticker, name, exchange, sector, industry, first/last seen, active status.
- `data/statistics/changes.parquet`: distinct values by ticker/metric/category. Not a daily snapshot of unchanged values.
- `data/financials/observations.parquet`: period-labelled raw statement observations and changed-value revisions.
- `data/execution_log.parquet`: extraction statuses.

## Known limitations / next engineering steps
- **No live extraction verified**: environment cannot resolve stockanalysis.com. Inspect real HTML, test every statement and the sector/industry profile layout. Some pages may be JS-rendered, unavailable, or require licensed access.
- **Exchange lists are not an exact common-stock or StockAnalysis-supported universe**. ETFs and obvious non-common names are filtered, but security type, exchange and coverage must be validated with a proper security master. Ticker changes are not automatically reconciled to the same issuer: the current hash-based ID is only a provisional identifier.
- **Missing ticker handling**: missing symbols are flagged inactive immediately in this prototype; production should require two confirmed source snapshots or a corporate-action feed before delisting. Historical facts are retained.
- **Period semantics**: labels are preserved as shown. Annual, quarterly, TTM, units and scaling are not yet reliably normalized. Do not use extracted values for financial calculations until verified.
- **Git growth**: rewriting large Parquet files causes Git history bloat. For 3k tickers and frequent updates, partition/compact files or use external object storage; GitHub repository is not an unlimited database.
- **Daily OHLCV**: select and license a market-data API; then implement adjusted prices, splits, dividends, incremental backfill and validations.
- **Data quality**: source timestamp, completeness and freshness checks must be expanded before production.
- **Access**: robots.txt checks are included but do not replace compliance with terms, licenses, and rate limits. No evasion of access restrictions.

## Suggested commit message
`feat: add dynamic stock universe and multi-statement parquet pipeline v2.0.0`

## v2.0.1 test configuration
Defaults to MU, AAPL, MSFT (custom universe, 3 tickers). Collection remains disabled until provider permissions are verified. After authorization, set `allow_automated_collection` to `true` in `config/settings.json`, replace `YOUR_EMAIL`, and run the workflow.


## v3.0.0 — FINVIZ overview snapshot (2026-11-23)

Adds `src/finviz.py` and `collect_finviz` setting. Preserves each FINVIZ snapshot
metric as an original label and raw value, including compound values. Records
are written to `data/finviz/snapshots.parquet`. Missing or changed HTML causes
a logged failure, not silently fabricated values. Sector and industry are best effort.

**Important:** No live FINVIZ HTML access or 3,000-ticker collection has been
validated. The unit tests use synthetic HTML. Do not enable automated collection
until permission for the intended providers, volumes and usage has been verified.
Set `allow_automated_collection=true` only after authorization, and replace
`YOUR_EMAIL` in `contact_user_agent`. For FINVIZ-only testing, set
`collect_stockanalysis=false` and `collect_finviz=true`. The dynamic universe
uses Nasdaq Trader exchange symbol directories and may include instruments
that are not supported by FINVIZ; unavailable symbols are logged.

Note: GitHub Actions will fail if any page fails. The pipeline is a testable
prototype, not yet a production-ready licensed bulk data feed.
