# Market Pipeline v3.0.4 — FINVIZ full snapshot extraction

## Changes (2026-11-23)
- Parses all metric/value pairs in FINVIZ snapshot table, not just first pair per row.
- Supports 12-cell rows (6 pairs) and wrapped-cell variants.
- Validates core metric labels and a minimum 40 fields; logs actual row cell counts and sampled labels when incomplete.
- Preserves compound and missing values unchanged.
- Uses `https://finviz.com/stock?t={TICKER}&p=d` for FINVIZ.
- Includes 72-metric synthetic regression fixture and additional parser tests.
- StockAnalysis collection disabled for initial FINVIZ-only validation.

## Run
1. Upload ZIP contents into your GitHub repository.
2. Review FINVIZ terms and confirm authorization for automated collection.
3. Only after authorization, set `allow_automated_collection` to `true` in `config/settings.json`.
4. Run the workflow. Check `[OK] ... metrics extracted` and the diagnostics artifact.
5. Compare saved values to the actual FINVIZ page before scaling up.

## Limitations
The parser is tested against synthetic HTML resembling the provided screenshot, not live FINVIZ HTML. A page rendering the full table in JavaScript or using a different structure may still need adaptation. Do not disable the minimum metric validation just to make collection pass. FINVIZ permissions and rate limits still apply. `config/settings.json` ships with automated collection disabled intentionally.

## Suggested commit message
`fix(pipeline): v3.0.4 - parse complete FINVIZ snapshot table and validate metrics`


## v3.0.5 — sector / industry dtype fix (2026-11-23)

- Initialize `sector` and `industry` as pandas nullable string columns.
- Repair dtype when loading existing Parquet files, including those written by v3.0.4.
- Apply to both FINVIZ and StockAnalysis profile update paths.
- Keep your existing `config/settings.json` when upgrading. The packaged config defaults to disabled collection; enable only after verifying source permissions.
- This release does not change the FINVIZ HTML extractor.

Commit: `fix(pipeline): v3.0.5 - repair sector and industry string dtypes`
