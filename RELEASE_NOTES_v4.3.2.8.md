# v4.3.2.8 Accounting Review Prototype

Added `fundamentals/accounting_v4328.py` with explicit dimension-verification requirements, consolidated equity calculations, liabilities fallbacks, diluted EPS fallback, and non-destructive scale anomaly detection. Added six synthetic regression tests using the numbers supplied in the user prompt. These are arithmetic fixtures, NOT independently verified SEC facts.

**Not integrated into the existing Company Facts collector or MongoDB repair workflow.** SEC `companyfacts` observations do not expose all filing-level dimension/context metadata; strict dimension verification requires filing-level XBRL parsing. No live MongoDB or SEC tests were performed. Do not enable APPLY based on these tests. No claim of resolving the 442 discrepancies or 4,803 EPS reviews.

Accounting caveat: redeemable NCI / temporary equity must be modeled as a separate claim rather than automatically added to permanent equity. Scale anomalies are review-only. Derived liabilities from combined liabilities-and-equity are review-only because the resulting balance equation is tautological.
