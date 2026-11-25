# MaketData v4.3.2.16 — clean Actions deployment

This package contains exactly four workflow YAML files. GitHub does **not** delete old workflow files when you upload only new files. Replace the **entire** `.github/workflows/` directory in your Git checkout and commit the deletions to `main`.

## Recommended deployment (local Git checkout)

1. Check out the existing `main` branch and back up any uncommitted changes.
2. Copy the contents of this ZIP into the checkout, overwriting files.
3. Remove any legacy `.github/workflows/*.yml` or `*.yaml` files not in the approved list below. The optional `bash scripts/deploy_clean_workflows.sh` stages deletion of tracked legacy workflow YAML files.
4. Run `python -m scripts.verify_workflows` and `python -m unittest tests.test_workflow_inventory_v43216 -v`.
5. Review `git diff --stat`, `git diff --cached --name-status`, and commit/push to `main`.
6. Check GitHub Actions sidebar after the commit; historical runs can still appear.

## Four approved workflows

- `collect.yml`: Market Data Collection (scheduled)
- `blackrock-universe-to-mongodb.yml`: Company Universe & SEC Sync (scheduled and manual)
- `largecap-fundamentals.yml`: SEC Fundamentals (Manual)
- `financial-quality-audit.yml`: Financial Quality Audit (Manual)

## Database initialization

1. Confirm repository secrets `MONGODB_URI` and `SEC_USER_AGENT`, and network connectivity to MongoDB.
2. Run **Company Universe & SEC Sync** with `sync_only=true` to synchronize SEC-matched profiles.
3. Review `UNIVERSE_SYNC` logs and database counts.
4. Run the same workflow with `sync_only=false`, `batch_size=30` to process one financial batch.
5. Scheduled runs advance the cursor only after the collector reports no failures.

**Scope warning:** Without a verified market-cap CSV, the ETF universe includes small caps and is **not** a $10B+ screen. BlackRock live downloads, SEC API availability, and MongoDB writes require runtime validation on GitHub. No production database changes are made by packaging this release.
