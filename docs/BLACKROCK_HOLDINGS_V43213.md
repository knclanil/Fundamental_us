# BlackRock ETF Holdings v4.3.2.13

## What works
- IWB (239707), IWM (239710), IWV (239714) official holdings endpoints.
- Parse each ETF's *actual* CSV schema (IWB includes Type, IWM/IWV do not).
- Validate holdings date, header, equity asset class, minimum row count, and cross-ETF snapshot date.
- Deduplicate by ticker and preserve membership flags.
- GitHub Actions scheduled refresh produces a downloadable **artifact**, not a git commit or database write.
- Uploaded Nov 24, 2026 CSV snapshots are bundled for reproducibility; use `data/blackrock_holdings_2026-11-24.csv` as collector input.

## Refresh automatically
Run GitHub Actions → **BlackRock ETF holdings refresh**. It attempts recent business dates and publishes `blackrock-holdings-validated`. If the provider is blocked, fails, or returns inconsistent files, no replacement artifact is published. The checked-in snapshot is preserved.

## Collect SEC fundamentals
Run **Fundamentals collector** with `universe=blackrock_holdings`, `universe_file=data/blackrock_holdings_2026-11-24.csv`, `limit=10`. This selects ETF constituents and matches SEC CIKs; **it is not a $10B+ screen**. For the strict market-cap filter use `us_large_cap` with independently sourced market-cap CSV. Do not substitute ETF position Market Value for issuer market cap.

## Important remaining work
- Scheduled ETF refresh currently produces an artifact, but does not automatically feed the refreshed artifact to the SEC collector or commit it to the repo.
- SEC collector still examines the first `limit` tickers per run; there is no pagination/cursor for full coverage.
- Automated verified issuer market-cap feed is not included. Foreign issuers may have different SEC Company Facts coverage.
- No live SEC or MongoDB writes were executed in this release.
