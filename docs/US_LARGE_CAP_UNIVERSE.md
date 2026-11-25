# U.S.-listed large-cap universe (v4.3.2.12)

Use `--universe us_large_cap --universe-file data/us_large_cap.csv` to collect U.S.-listed issuers with **market capitalization >= USD 10 billion**, including foreign-domiciled issuers when SEC Company Facts is available.

**SEC Company Facts does not supply market capitalization.** Provide a legally obtained, current market-cap export. The repository intentionally does **not** contain a fabricated large-cap universe or a paid-provider API key. The source CSV must have these headers:

```csv
ticker,market_cap_usd,exchange,as_of,source
```

`market_cap_usd` must be a USD number (not millions/billions), `as_of` an ISO date, `source` the provider name, and `exchange` NASDAQ, NYSE, NYSE AMERICAN, NYSE ARCA, or AMEX. Securities without an SEC ticker-to-CIK match are skipped. Foreign issuers may have incomplete Company Facts coverage. A large-cap classification is only as current as the input snapshot; refresh it periodically.

## GitHub Actions (main branch)

Open **Actions → Fundamentals collector → Run workflow**. Choose `universe=us_large_cap`, `universe_file=data/us_large_cap.csv`, `limit=10` (first run), and `force_refresh=false`. Commit your CSV to the repository first. The weekly scheduled run remains `sp500` unless deliberately changed. `limit` is **not pagination**: repeated runs with the same CSV and limit will keep checking the same first entries. For complete large-cap coverage, implement cursor/batch support before increasing the run scope.

No MongoDB collection migration is required. The existing company profiles gain market-cap, source, as-of date and exchange fields when successfully collected. No historical financial records are deleted. Do not include API keys or licensed raw provider datasets in a public repository.
