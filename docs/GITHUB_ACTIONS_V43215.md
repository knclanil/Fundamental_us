# GitHub Actions cleanup — v4.3.2.15

Four active workflows remain:

| Workflow | Trigger | Purpose |
|---|---|---|
| Market Data Collection (`collect.yml`) | Daily schedule + manual | Existing market data ingestion |
| Company Universe & SEC Sync (`blackrock-universe-to-mongodb.yml`) | Tuesday–Saturday schedule + manual | Refresh ETF universe, sync MongoDB company profiles, collect next SEC batch |
| SEC Fundamentals (Manual) (`largecap-fundamentals.yml`) | Manual only | Targeted SEC collection, alternative universe selection and diagnostics |
| Financial Quality Audit (Manual) (`financial-quality-audit.yml`) | Manual only | Read-only financial audit; its `--expected 500` setting is a historical S&P 500 baseline, not a large-cap completeness test |

The old separate BlackRock holdings workflow was removed because the scheduled company-universe workflow already fetches holdings. Obsolete SEC proof-of-concept, repair, migration, and cleanup workflows were removed from `.github/workflows` to avoid clutter and accidental production writes. Their underlying Python modules and documentation remain available.

**Deployment to `main`:** Replace `.github/workflows` with the four files in this release. When uploading via the GitHub website, also **delete the nine old workflow YAML files** from the repository; uploading only new files will NOT delete existing workflows. Verify the Actions tab after commit.

**Secrets:** `MONGODB_URI` and `SEC_USER_AGENT` are needed for SEC sync. No live database changes are made by this release itself.

**Safety:** The two SEC-writing workflows use the same GitHub Actions concurrency group to prevent overlap. The existing market-data workflow retains its own concurrency group.

**Large-cap limitation:** The scheduled ETF universe is NOT automatically filtered to $10B market cap unless a verified market-cap file is supplied.
