# v4.3.2.10 — Repository housekeeping and read-only database inventory

- Organized prior version release notes under `docs/releases/`.
- Expanded `.gitignore` to exclude local secrets, Python caches and generated reports.
- Added `scripts/db_inventory.py` for read-only MongoDB collection/index/storage inventory.
- Added operational guide `docs/REPOSITORY_AND_DATABASE_OPERATIONS.md`.
- Kept all existing collectors, workflows, tests and tracked datasets unchanged.
- No MongoDB cleanup, schema changes, or index drops were performed.
