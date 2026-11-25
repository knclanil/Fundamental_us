#!/usr/bin/env bash
# Run from the extracted repository root after copying it into your Git checkout.
# Only removes obsolete YAML files from .github/workflows. Does NOT push or alter MongoDB.
set -euo pipefail
cd "$(dirname "$0")/.."
python -m scripts.verify_workflows
if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo 'Not a Git checkout. Copy the package into your local Git checkout first.' >&2
  exit 1
fi
for file in $(git ls-files '.github/workflows/*.yml' '.github/workflows/*.yaml'); do
  case "$file" in
    .github/workflows/collect.yml|.github/workflows/blackrock-universe-to-mongodb.yml|.github/workflows/largecap-fundamentals.yml|.github/workflows/financial-quality-audit.yml) ;;
    *) git rm -- "$file" ;;
  esac
done
git add .github/workflows scripts/verify_workflows.py tests/test_workflow_inventory_v43216.py
echo 'Review with: git status --short; then commit to main.'
