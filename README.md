# MaketData SEC MongoDB POC v4.0.3

## Installation in existing repository
Copy **all** included files into the repository root, keeping paths unchanged. In particular replace `src/collect.py`, `tests/test_core.py`, and `.github/workflows/sec-poc.yml`; add `requirements-sec-poc.txt`. Do not delete old `data/`, legacy tests or v3 workflows.

## GitHub secrets
- `MONGODB_URI`: MongoDB Atlas database connection URI (do not commit it).
- `SEC_USER_AGENT`: SEC-compliant app identity with real contact email.

In Actions select **SEC fundamentals POC**, run with limit=10, refresh_days=7.

## Design notes
- Uses SEC official JSON APIs and PyMongo. This is the **existing v4.0 POC workflow**, not the separate v4.1 `SEC MongoDB v4` workflow.
- Stores full SEC Company Facts response per company; larger issuers may exceed MongoDB 16MB document limit. Production migration should use concept/unit partitioning.
- SEC ticker list is CIK sorted; this is a proof of concept, not a market-cap ranking.
- MongoDB connectivity and live SEC requests require GitHub secrets and cannot be validated offline.
