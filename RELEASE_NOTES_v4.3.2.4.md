# v4.3.2.4 — Financial quality audit test compatibility

Date: 2026-11-25

## Change
- Updated `tests/test_quality_audit.py` to assert report schema version `4.3.2`, matching `fundamentals/quality_audit.py` (`VERSION = '4.3.2'`).
- No database, collector, CIK resolution, or audit logic changes.

## Validation
- Python syntax compilation completed.
- The test suite requires `pymongo`; this environment lacks the dependency and cannot install it offline. Run the GitHub Actions financial quality audit workflow to execute tests with project requirements installed.

## Suggested commit
`test(v4.3.2.4): align quality audit report version assertion`
