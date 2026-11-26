# MaketData v4.3.2.23 — Offline Testing Report

## Scope
This is a **testing-only** release based on the supplied v4.3.2.22 ZIP. No production collector, normalization, MongoDB, or workflow code was changed. Added ten focused safety regression tests in `tests/test_safety_regression_v43223.py`.

## Actual execution
- Python compilation of `fundamentals` and `tests`: **PASS**.
- `pytest -q tests/test_safety_regression_v43223.py tests/test_fact_alignment_v43221.py tests/test_fiscal_lookback_v43222.py tests/test_normalization_v4329.py`: **20 passed**.
- Full `pytest -q`: **BLOCKED during collection**, 16 import errors due to `ModuleNotFoundError: No module named 'pymongo'`. This is an environment/dependency blocker, not evidence those tests would pass or fail with dependencies installed.
- Live SEC validation: **NOT RUN**.
- Live MongoDB validation: **NOT RUN**.
- GitHub Actions scheduled execution: **NOT RUN**.
- Performance/load tests: **NOT RUN**.

## Safety regression scenarios exercised
1. Preserve already reconciled records.
2. Reject a candidate from another period.
3. Reject the wrong SEC form.
4. Do not combine facts from different accessions.
5. Reject incomplete candidates.
6. Accept compatible noncontrolling-interest component.
7. Use 10-Q for quarterly alignment.
8. Maintain idempotency after a successful alignment.
9. Reject an unreconciled candidate.
10. Retain source accession and selection method.

## Important limitations
- These tests use synthetic SEC facts and exercise only a small part of the 112-case master plan.
- They do not validate Agilent's live SEC numbers or establish any improvement in the production audit baseline.
- `context_dimensions_verified=False` in the existing alignment code means accession agreement alone is not proof that full XBRL context is compatible.
- No production remediation was implemented or claimed.

## Next validation steps
1. Install repository dependencies in an isolated CI runner, then execute the complete pytest suite.
2. Run targeted live SEC collection for `A` against a backup/test database.
3. Run the read-only Financial Quality Audit and compare the same company/period issue keys to the baseline.
4. Validate MongoDB idempotency and source provenance before any broad reprocessing.
