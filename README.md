# MaketData v3.2.0 — Market-cap priority + recoverable backups

Version: 3.2.0 (2026-11-24)

## Changelog
- 3.2.0: prioritize known mega-cap, large-cap, mid-cap, then smaller stocks; skip snapshots refreshed in the past 24h; optional authorized market-cap CSV seed; backup all data as workflow artifacts even on failure; protect against non-fast-forward push by refusing to overwrite remote.
- 3.1.3: fund detection, 404 skips, failure queue.

## Critical limitation
Exchange symbol directories **do not contain market capitalization**. The pipeline ranks stocks using **existing FINVIZ snapshot Market Cap values** and/or `config/market_caps.csv` with columns `ticker,market_cap_usd` from a provider you are authorized to use. An example file is supplied but is **not** used. Without a comprehensive seed, uncollected stocks are **unknown cap** and processed after known-cap stocks, not truly large-cap-first. To guarantee mega/large/mid-first for all ~4,919 tickers, supply an up-to-date, licensed market-cap seed covering the universe. No market-cap values are invented.

## Deploy
1. Extract ZIP into the existing repo. **Do not delete or overwrite existing `data/` files**. Keep your existing `config/settings.json` authorized-access settings; merge the new `collection_strategy`, `market_cap_seed_csv`, and `refresh_after_hours` keys.
2. Optionally add `config/market_caps.csv` from a permitted data provider. The example is illustrative only.
3. Keep `allow_automated_collection` disabled until you have verified provider permissions. This package ships with it disabled.
4. Commit the code, then run Actions > Collect market fundamentals. The workflow is scheduled daily at 03:15 UTC.
5. On failed pushes, download the `market-data-<run>-<attempt>` artifact before it expires. **Do not blindly overwrite or force-push** the repo: reconcile the saved Parquet and state files with current main.

## Collection logic
- Market cap thresholds (USD): mega >=200B; large >=10B; mid >=2B; small >=300M; micro >=50M; nano <50M; unknown last.
- First prioritize not-yet-collected stocks within each cap tier; stocks with a `Price` observation younger than 24h are skipped.
- Already collected but stale stocks can be refreshed. Source metrics with changed values retain revisions as in v3.1.3.
- `failed_tickers.json` persists errors, but retries remain subject to priority/refresh logic.
- `cursor.json` is not used in priority mode; existing cursor is left untouched for rollback.
- A `git push` conflict is not resolved automatically because binary Parquet files cannot be safely rebased. An artifact backup is uploaded even if push fails.
- Existing ticker filtering and FINVIZ page validation remain unchanged.

## Checks
Run `python -m pytest -q`. Live collection and provider permissions must be validated in GitHub Actions.

Suggested commit: `feat(pipeline): v3.2.0 market-cap priority, incremental selection and artifact backups`


## v3.2.1 — Alpha Vantage free-tier market-cap enrichment (2026-11-24)

- Set GitHub repository Actions secret `ALPHA_VANTAGE_API_KEY`; never commit the key.
- The `OVERVIEW` API is used only to enrich previously unknown market caps, not to replace FINVIZ extraction.
- `data/state/alpha_market_caps.json` caches successful and unavailable lookups; `data/state/alpha_quota.json` tracks requests used per UTC date. Both must be committed/preserved with `data/`.
- Default budget is **20 requests per UTC day**, below the commonly published free allowance of 25/day. Confirm the provider's current quota and your account entitlement; set `alpha_vantage_daily_budget` lower if needed.
- Market caps from the local cache feed the existing priority sorter. Unclassified symbols remain last; a complete guaranteed large-cap-first ranking still requires full-universe classification or a licensed seed feed.
- If the secret is absent, the pipeline still works with existing FINVIZ market caps and an optional authorized CSV.
- To prevent spending quota across concurrent runs, use the workflow concurrency group and keep state commits successful. If Git push fails, **stop subsequent runs until you recover the artifact and reconcile the quota state**, since the runner-local counter may not have been persisted.
- The workflow artifact backs up the `data/` folder on success or failure, with 30-day retention. It is not permanent storage. Git push retries use fetch/rebase; Parquet conflicts require manual reconciliation, never force-push.
- Existing `config/settings.json` in your repo is user-specific: merge the new three `alpha_vantage_*` settings; do not overwrite your working provider permissions.

Suggested commit: `feat(pipeline): v3.2.1 add free-tier Alpha Vantage cap enrichment and quota cache`

## v3.2.2 — GitHub Actions configuration fix (2026-11-24)

- `config/settings.json` sets `allow_automated_collection: true` at the user's request. **Only run automated collection where source terms/permissions allow it.**
- Workflow checks that `ALPHA_VANTAGE_API_KEY` exists before extraction and reports an actionable error without exposing the key. GitHub secrets **cannot** be created or included in a ZIP; add it in repository Settings > Secrets and variables > Actions.
- Existing collection, checkpoint, artifact backup and Git push retry logic retained.
- Preserve the repository's `data/` directory and merge configuration changes if your live settings differ.

## v3.2.3 — Smart ticker selection and 404 recovery (2026-11-24)
- Reconstruct FINVIZ unsupported ticker history from existing `data/execution_log.parquet` on first run; no historical data deletion or reset.
- Persist `data/state/finviz_unsupported.json`, with a configurable 30-day cooldown for provider HTTP 404 and fund-snapshot skips. This is provider-specific, not a delisting judgment.
- Exclude cooldown tickers from both market-cap selection and Alpha Vantage discovery.
- Market-cap value `0` is treated as unknown, not a valid known capitalization.
- Select up to `max_attempts_per_success` (default 3) candidate tickers per desired success; stop once target successes are achieved. A batch can return fewer successes if the candidate pool or attempt budget is exhausted.
- Report attempted vs successful ticker counts; zero-success attempted priority batches now fail rather than silently passing. Artifacts and local data checkpoint remain available on failure.
- No speculative dot-to-hyphen FINVIZ symbol rewrites are made; provider mappings must be verified before enabling them.
- Existing settings and `data/` should be preserved when deploying; merge new settings rather than overwrite customized values.
