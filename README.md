# Market Data Pipeline v3.1.0 — dynamic universe, rotation, quality gates

Built on v3.0.5; preserves the verified FINVIZ snapshot extractor and StockAnalysis modules.

## Configuration

- `universe: "custom"`: read `config/tickers.csv`. `universe: "dynamic"`: retrieve exchange symbol directories. Exchange directories include instruments that may not be ordinary operating-company stocks; filters are approximate and need review.
- `max_tickers`: number to process per run; `0` processes all selected tickers (not recommended without provider authorization).
- `rotate_tickers: true`: with a positive max_tickers, advances a persisted cursor **only after a fully successful run**, so successive scheduled runs cover more symbols. This is batch rotation, **not** a guarantee of change-based HTTP skipping.
- `finviz_min_metrics` and `finviz_required_metrics`: fail if a page has too few unique labels or lacks required labels. Some legitimate stocks may not have all metrics; adjust only after inspecting diagnostics.
- `allow_automated_collection` remains **false** by default. Enable only after confirming the source permits the intended volume and use. FINVIZ and StockAnalysis are independent sources.

## Rollout

1. Upload all ZIP files into the repository, preserving the existing authorized `config/settings.json` (merge new keys rather than overwriting your contact/permissions).
2. Run `python -m pytest -q`, then `python src/pipeline.py --dry-run`.
3. Start with `universe: "custom"`, `max_tickers: 3`, and `rotate_tickers: true` after permissions are confirmed.
4. Test `universe: "dynamic"` with `max_tickers: 25`, inspect `data/execution_log_latest.csv`, `data/dimensions/instruments.parquet`, and `data/finviz/snapshots.parquet`.
5. Increase gradually after confirming access rights, quality, and Git repository growth.

## Safeguards and limitations

- The dynamic universe refuses an unexpected >35% shrink versus the previous stored dimension (for dynamic runs); missing symbols are marked inactive for review, **not confirmed delisted**.
- Custom runs retain existing instruments instead of marking non-custom symbols inactive.
- Snapshot Parquet preserves distinct raw values; identical repeated observations are deduplicated. **This is change-based storage, not a complete daily point-in-time snapshot**.
- Git history grows with each rewritten Parquet. This release does **not** implement immutable partitioned historical storage or a stable identifier across ticker renames.
- Collection and parsing against live sites were **not tested here**. The existing user's successful v3.0.5 GitHub run is the baseline.
- The cursor advances only on a completely successful run. Partial failures are retained in diagnostic artifact but will retry the same batch.

Suggested commit: `feat(pipeline): v3.1.0 add dynamic universe rotation and quality gates`


## v3.1.1 — 2026-11-23
- Exclude clearly labeled units, warrants, rights, preferred shares, notes, funds and trusts from exchange directories using noncapturing regex groups; no suffix-only exclusions. Security-name filtering is best effort and may exclude some valid companies.
- Treat **FINVIZ HTTP 404 only** as an expected `skipped` result. Other HTTP errors and parsing/quality failures still fail the batch. A batch with no successful pages also fails.
- Advance `data/state/cursor.json` after a successful batch containing expected skips; commit the cursor with data using the existing workflow. If a batch has unexpected errors, it does not advance.
- Avoid concatenating an empty `missing` frame; cast sector and industry columns explicitly.
- Keep your existing authorized `config/settings.json` when deploying; the packaged config intentionally disables collection until permission is confirmed.
- Filtering is not a guarantee that every discovered symbol is an operating-company common stock.
