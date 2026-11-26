# Automated Tests — Setup

Workflow: `.github/workflows/automated-tests.yml`

- Runs on every push to `main`, on pull requests targeting `main`, and via **Actions → Automated Tests → Run workflow**.
- Installs Python 3.11, project requirements, pytest, and pytest-cov.
- Compiles source and runs the complete existing test suite.
- Uploads a JUnit XML report and text log as a GitHub Actions artifact even when pytest fails.
- Does not require MongoDB credentials and does not deliberately run SEC collection or write production data.
- Some existing tests may require external services; any such tests must be isolated or mocked before the workflow can be considered fully offline.

## Deploy

Copy the contents of `MaketData-main/` into the repository root, including the hidden `.github/` folder. Commit to `main`. Open **Actions → Automated Tests** to see the automatic run. To run again, select **Run workflow**.

## Interpret

A green check means the configured test commands passed, not that live SEC data and production MongoDB have been verified. Download the `automated-test-results-*` artifact for test details.
