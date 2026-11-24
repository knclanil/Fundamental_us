# MaketData v4.1.1 — S&P 500 Fundamentals (Free-tier POC)

## What changed
Nasdaq screener was unreliable in GitHub Actions. This release discovers the **S&P 500 constituents** from Wikipedia, joins tickers to SEC CIKs, and collects five years of normalized annual and quarterly fundamentals into MongoDB Atlas.

**Important:** S&P 500 membership is NOT the same as market capitalization >= $10 billion. This release is an S&P 500 proxy, not the previously proposed complete US large-cap universe. Market caps are not supplied by this feed.

If the live constituent table cannot be read, the workflow explicitly logs a warning and uses a checked-in **30-ticker partial bootstrap** for a limited proof of concept. This is NOT a full S&P 500 list. No scraping of Nasdaq is attempted.

## Install into existing repository
Copy `fundamentals/`, `data/sp500_bootstrap.csv`, `tests/test_largecap.py`, `requirements-largecap.txt`, and `.github/workflows/largecap-fundamentals.yml` into your existing MaketData repository. Preserve the working v4.0.3 SEC POC and all existing data. You may merge this README rather than overwrite your existing README.

## Secrets
GitHub Actions secrets: `MONGODB_URI` and `SEC_USER_AGENT` (valid contact email). Database defaults to `maketdata`.

## Run
Actions > **S&P 500 fundamentals v4.1.1** > Run workflow, limit=10, refresh_days=7. Logs show the universe source and a collection summary. Increase the limit only after validating MongoDB data and storage.

## MongoDB collections
`companies`, `financial_annual`, `financial_quarterly`, `largecap_collection_state`, `pipeline_runs`. Existing `company_facts_raw` is untouched.

## Cost and correctness cautions
- Free Atlas M0 storage is limited. Monitor usage; no paid upgrade is automatic.
- SEC XBRL concepts differ by company. The normalizer extracts a common subset and does not guarantee every statement metric.
- A five-year period filter is applied to new records; older v4.1 records are not automatically deleted, to avoid accidental loss on incomplete SEC responses.
- Annual and quarterly periods depend on available SEC `frame` values; some fiscal-year records may be absent.
- The script's `--min-market-cap` option is retained for CLI compatibility but **does not filter** S&P 500 membership by market cap.
- SEC downloads respect a minimum request interval and bounded retries.
- The universe feed can fail; fallback is explicitly partial, and no empty list is silently treated as success.

## Validate locally
`pip install -r requirements-largecap.txt` then `python -m unittest discover -s tests -p 'test_largecap.py' -v`.
