# v4.3.2.20 — Financial reconciliation investigation (non-destructive)

Based on the November 26, 2026 v4.2.1 financial quality audit.

- Adds read-only balance-sheet equation alternatives and SEC metric provenance to quality audit issue details.
- Adds `scripts/build_reconciliation_review.py` to generate a per-company investigation queue from the audit ZIP.
- Does **not** alter stored financial facts, rewrite liabilities/equity, or advance collection checkpoints.
- The existing collector and PFBC 404 handling are preserved.

## Targeted review queue

```bash
python scripts/build_reconciliation_review.py --audit "maketdata-financial-quality-v4.2.1 (7).zip" --output reconciliation_review.csv
```

Investigate the highest residuals first, compare SEC filing context and accession for assets, liabilities, and equity, then apply independently validated corrections via the existing repair-validation pipeline. The queue is not a write-back tool.

## Validation

```bash
python -m unittest tests.test_reconciliation_review_v43220
# Install requirements before running the full suite (pymongo required):
# python -m unittest tests.test_v432_balance
```

**Important:** The new diagnostics are hypotheses, not proof that any specific metric is wrong. A database repair and targeted SEC recollection have intentionally not been automated because the audit CSV lacks source filing facts needed to justify edits.
