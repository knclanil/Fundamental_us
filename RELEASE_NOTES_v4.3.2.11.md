# v4.3.2.11 — Configurable company universe

- Added `sp500` (default), `tickers`, `custom` CSV, and `sec_all` universe modes.
- Added workflow_dispatch universe inputs; scheduled collection still defaults to S&P 500.
- Preserved existing financial collections and identity checks; no schema migration or destructive cleanup.
- Added tests for mode selection and CSV validation.
- Added documentation for expanding into mid/small-cap watchlists and storage limitations.
- `sec_all` means SEC ticker-feed coverage, **not** all public companies and **not** a market-cap classification.
- Known limitation: `--limit` is not pagination; repeated runs select the same leading tickers.
