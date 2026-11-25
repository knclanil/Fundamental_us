# MaketData v4.3.2.18
- Added opt-in `full_collection` GitHub Actions input.
- Process multiple sequential SEC batches per run, with MongoDB checkpoint after each successful batch.
- Automatically dispatch the next run when the time budget expires, without adding a fifth workflow.
- Stop cleanly at the end of the universe, and do not silently skip blocked identity profiles.
- Added unit tests for batch boundaries and GitHub output metadata.

Suggested commit message: `feat: add resumable unattended SEC full collection (v4.3.2.18)`
