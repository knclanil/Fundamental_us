# v4.3.2.12 — U.S.-listed large-cap selection

- Added opt-in `us_large_cap` mode with strict >= USD 10B market cap filter using externally sourced CSV.
- Accepts U.S.-listed foreign issuers when SEC CIK mapped; preserves market-cap provenance in company profile.
- Fails closed on missing/invalid input; avoids treating SEC ticker feed as a market-cap provider.
- Added four unit tests and workflow input. No database deletions, no automatic financial repair.
- Known limitation: first-N `limit` is not pagination; weekly schedule still defaults to S&P 500.
