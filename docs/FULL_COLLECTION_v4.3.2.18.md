# v4.3.2.18 — Automatic full-universe collection

Use **Actions → Company Universe & SEC Sync → Run workflow** on `main`:
- `full_collection`: **true**
- `sync_only`: false
- `batch_size`: 100
- `market_cap_file`: blank for unfiltered BlackRock ETF universe; provide a verified CSV to apply the $10B screen.

The job processes sequential batches until its 105-minute internal time budget is reached, then dispatches the same workflow automatically. A MongoDB checkpoint is saved after every successful batch. The existing GitHub Actions concurrency group serializes runs. The four existing workflow files are preserved.

**Operational limitations:** If a batch fails, the workflow stops and does not auto-retry or advance the checkpoint; inspect the logs and manually re-run Full Collection after resolving the issue. GitHub Actions dispatch requires `actions: write` permission and organization policy allowing `GITHUB_TOKEN` to trigger workflow dispatch. If dispatch is rejected, rerun Full Collection manually; it resumes at the checkpoint. Do not run overlapping manual collection workflows. If holdings or market-cap CSV content changes, the snapshot hash changes and the existing cursor restarts at zero. A completed snapshot does not restart when Full Collection is selected again.

**Quality:** Existing financial quality warnings remain; the full collection mode does not repair or certify SEC accounting data. Run the separate Financial Quality Audit when collection finishes. `skipped` means the collector did not refresh that issuer; it is not proof of full financial coverage.
