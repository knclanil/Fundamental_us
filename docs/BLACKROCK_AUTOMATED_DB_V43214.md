# v4.3.2.14 — BlackRock holdings → MongoDB

## One-time setup

Commit this release to **main**. In GitHub repository Settings → Secrets and variables → Actions, configure `MONGODB_URI` and `SEC_USER_AGENT` (SEC-compliant contact-bearing user agent). Ensure MongoDB Atlas network access permits GitHub Actions runners, using an appropriately secured connection.

Run **BlackRock ETF universe to MongoDB v4.3.2.14** with `sync_only=true` to populate/refresh company profiles for every SEC-mapped ETF issuer. Then run it with `sync_only=false` for SEC fundamentals in resumable batches. The scheduled job processes 30 issuers per run, advancing a MongoDB cursor only on successful batches. A full cycle takes multiple runs. Re-running sync does not delete historical companies or financials.

## Eligibility and limitations

**ETF membership is not a $10 billion market-cap test.** Without a verified external `market_cap_file`, this workflow syncs SEC-mapped IWB/IWM/IWV equity issuers regardless of size. To strictly collect >=$10B, supply a current `ticker,market_cap_usd,exchange,as_of,source` CSV through the workflow input. This release does **not** automatically source issuer market caps. BlackRock's ETF `Market Value` is a position value, not issuer market cap.

Live BlackRock fetch is attempted; if it fails, a checked-in validated 2026-11-24 snapshot is used. This prevents empty universe writes but means holdings may become stale. Live source availability and MongoDB credentials must be verified in GitHub Actions; no production DB is accessible from the build environment.

The collector preserves its existing financial normalization and storage behavior. `companies` is populated first with discovered company profiles; these **do not imply SEC financials have already been collected**. Existing issuer CIK conflicts are skipped and counted, not overwritten. Existing financial records are not deleted by profile synchronization. `universe_sync_state` holds the resumable batch cursor.

## Local dry run (requires read access to MongoDB and SEC)

`python -m fundamentals.automated_universe --dry-run --holdings-file data/blackrock_holdings_2026-11-24.csv`

## Operational checks

Inspect the `UNIVERSE_SYNC` and `BATCH_COMPLETE` logs. Check `db.companies.countDocuments({universe_source:'blackrock_etf_holdings'})`, `db.universe_sync_state.findOne({_id:'blackrock_etf_collection_cursor'})`, and the existing `largecap_collection_state` collection. An ETF constituent that does not match SEC's ticker map is excluded, not assigned an invented CIK. A failed batch does not advance the cursor; subsequent runs retry it.
