# v4.3.2.7 — Financial accuracy evidence and safety update

## Changes
- Review-only equity replacement proposals require direct Assets, Liabilities and StockholdersEquity SEC facts from the **same accession** and balance-sheet reconciliation. These are NOT automatically written because SEC Company Facts does not prove all filing-level dimensional contexts.
- Explicitly report missing EPS source values by period, rather than silently omitting them from repair details.
- Retain existing v4.3.2.6 missing-field guarded repair and CIK resolution; preserve existing non-null values.
- New GitHub workflow and three regression tests.

## Limitations and next required work
This is **not** a verified correction of 442 balance sheets or 4,107 conflicts. Such claims require checking filing-level XBRL contexts, reporting dimensions, company-specific tags and the actual MongoDB write results. No automatic overwrite of existing values or deletion of obsolete XOM-associated records is included.

## Run
Actions → Financial integrity v4.3.2.7 - full SEC repair review → tickers ALL → apply_repair false.
Inspect repair_details.csv for EQUITY_REPLACEMENT_REVIEW, EPS_SOURCE_MISSING_REVIEW and existing BALANCE_REVIEW rows.
