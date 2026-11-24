# MaketData v4.1.0 — US large-cap fundamentals

**Scope:** US-listed common stocks with market capitalization >= $10 billion; SEC financial facts, 5-year window, MongoDB Atlas free tier. Daily OHLCV and technical analysis are intentionally out of scope.

## Installation (additive, safe)

Copy `fundamentals/`, `tests/test_largecap.py`, `requirements-largecap.txt`, and `.github/workflows/largecap-fundamentals.yml` into the root of your existing MaketData repository. **Do not overwrite** the working `src/` code or `.github/workflows/sec-poc.yml`. Commit the new files. Set existing `MONGODB_URI` and `SEC_USER_AGENT` repository secrets. Run **Actions → Large-cap fundamentals v4.1 → Run workflow**, with `limit=10` initially.

## Behavior and caveats

- The free Nasdaq screener endpoint is **unofficial/undocumented** and may block GitHub Actions or change its response. The collector fails rather than silently falling back to an incorrect large-cap list. Market caps are point-in-time snapshots, not SEC facts.
- SEC CIK matching uses the SEC public ticker list. Some eligible securities cannot be mapped; these are skipped. This is not a complete proof of US domicile or common-share class. Validate issuer domicile and security type before treating the universe as exhaustive.
- Financial values use SEC XBRL `CY...` frames to avoid mixing annual, discrete-quarter and year-to-date figures. Companies without these tags/frames can be incomplete. Bank/insurer-specific line items are not covered. Financial data are *not audited by this pipeline*.
- A five-year date window can include six calendar-year labels near a year boundary. Quarterly reporting periods may be fewer than 20.
- Financial collection refreshes 7 days after last success; weekly scheduled runs process the top 100 eligible companies by market cap by default. To cover more, run manually with a larger limit; consider Actions runtime and SEC rate limits. A `limit` counts companies examined, including skipped companies.
- Existing `company_facts_raw` documents remain untouched. **Do not delete them** until you validate normalized records and back them up. New data goes into `financial_annual` and `financial_quarterly`.
- Only `financial_annual`/`financial_quarterly` records for successfully refreshed companies are pruned. A failed fetch preserves previously stored financials.
- GitHub Actions and MongoDB free tiers have quotas and may change; $0 is a target, not a guarantee. Monitor Atlas usage.

## MongoDB inspection

Data Explorer → `maketdata` → `financial_annual` or `financial_quarterly`; filter `{"ticker":"AAPL"}`. View `pipeline_runs` for run counts. The new pipeline uses `largecap_collection_state` to avoid skipping companies because of old raw-data collection state.

## Test locally

```bash
python -m pip install -r requirements-largecap.txt
python -m unittest discover -s tests -p test_largecap.py -v
```

## Important

This is an additive release. Keep the old SEC POC workflow disabled on schedule (or manual only) to avoid further raw fact growth. The new workflow does not write raw SEC payloads.
