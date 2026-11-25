# MaketData repository and MongoDB housekeeping

## Scope and safety

This release reorganizes documentation and adds a **read-only** database inventory.
It does not connect to Atlas, delete collections, drop indexes, delete data, or
change financial normalization, scheduled collection, or existing workflows.
No collection is considered unused solely because its name looks old.

## Code ownership map

| Path | Current responsibility | Cleanup decision |
| --- | --- | --- |
| `fundamentals/` | S&P 500 SEC Company Facts and normalized statements | Retain |
| `src/` | Earlier market/Finviz/Alpha Vantage pipeline | Retain until workflow usage verified |
| `v4_mongodb/` | Earlier SEC MongoDB collector | Retain until usage verified |
| `tests/` | Regression suite | Retain |
| `.github/workflows/` | Production, manual and historical jobs | Retain until owners and last runs verified |
| `data/` | Bootstrap, state and historical Parquet outputs | Retain; audit tracking policy |
| `docs/releases/` | Versioned historical release notes | Consolidated here |
| `scripts/` | Read-only operational utilities | Added |

## Database inventory

Install `requirements-largecap.txt`, set the existing `MONGODB_URI` secret
and optionally `MONGODB_DATABASE` (defaults to `maketdata`), then run:

```bash
python -m scripts.db_inventory --output artifacts/db-inventory.json
```

The inventory records collection names, counts, logical/storage/index bytes,
and index definitions; **not document values**. Keep output out of Git.
If `collStats` is denied by Atlas permissions, request read-only database stats
access; do not broaden to write permissions merely to inspect storage.

## Collection retention policy (proposal; not executed)

- **Core**: `companies`, `financial_annual`, `financial_quarterly`,
  `largecap_collection_state`: keep, confirm actual keys and indexes.
- **Recovery**: `financial_duplicate_archive`, `financial_period_archive`:
  retain until backup and rollback windows are explicitly approved; never
  attach a TTL without a recovery decision.
- **Legacy candidates**: `sec_facts`, `company_facts_raw`, `collection_state`,
  and other collectors' collections: inspect active workflows and last write
  times first. Do not delete by name.
- **Reports and diagnostics**: prefer bounded GitHub Actions artifacts rather
  than writing full raw SEC payloads or stack traces into MongoDB.

### Storage reduction procedure

1. Record inventory and Atlas storage metrics before any change.
2. Classify collections by producer, consumer, retention requirement, and
   backup/restore plan; mark uncertain collections as **keep**.
3. Review actual index usage with Atlas index insights or `$indexStats` where
   permitted; do not drop unique constraints or indexes from `migrate.py`.
4. Archive and verify recovery copies before any approved deletion.
5. Apply one reversible change at a time, measure actual allocated storage
   afterwards (deleting documents may not immediately reduce disk allocation).

## Logging policy

Use Python `logging` with JSON-formatted **bounded** events for production:
`timestamp`, `level`, `event`, `run_id`, `ticker`, `cik`, `stage`, `duration_ms`,
`error_code`, `retryable`, and a sanitized exception class. Never log the
MongoDB URI, SEC tokens, full SEC responses, or financial document dumps.
Use `INFO` for company/period summaries, `WARNING` for recoverable gaps,
`ERROR` for failed companies, and `DEBUG` only for local troubleshooting.
GitHub Actions logs should have a short retention period consistent with your
operational needs. Record per-run aggregates; avoid one log record per fact.

## Next steps requiring Atlas access / explicit approval

- Determine real storage hotspots and redundant indexes from inventory.
- Determine which legacy workflows are still active before removing code.
- Define retention durations and backups for old state/log collections.
- Add structured logging to collectors without changing their business logic.
- Write a separate reviewed migration for each approved destructive operation.
