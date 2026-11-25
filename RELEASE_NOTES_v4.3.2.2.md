# MaketData v4.3.2.2 — SEC CIK Sync

- Official SEC ticker map fetched once per run via existing `SecClient` with SEC_USER_AGENT and >=0.1-second pacing.
- Canonicalize dotted tickers to hyphenated symbols and CIKs to ten-digit strings.
- Dry-run default; explicit `--apply` updates `companies` and archives original profiles for CIK changes.
- Mark unmatched / specified legacy company profiles as `untracked_legacy_or_orphan`; do not delete financial history.
- Collector now blocks on stored-vs-SEC CIK mismatch and known XOM issuer identity conflict before financial writes.
- SEC ticker mapping is not a verified active-issuer registry or S&P 500 constituent source.
- **Known issue:** SEC mapping previously returned XOM=2115436 (ExxonMobil Holdings Corporation). This conflicts with Exxon Mobil Corporation CIK 34088. The workflow intentionally fails closed rather than overwrite XOM with a subsidiary. This requires an issuer-verified override before recollecting XOM.
- Existing financial data is not automatically migrated across CIK identities. Audit prior XOM partial records separately.
- No live SEC/MongoDB test was performed.

Commit: `fix(v4.3.2.2): sync SEC CIKs and block incorrect issuer recollection`
