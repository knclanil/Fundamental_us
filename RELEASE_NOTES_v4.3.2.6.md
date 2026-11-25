# v4.3.2.6 — Full-universe financial repair review and identity fix

## Confirmed root causes addressed

1. `financial_repair --tickers ALL` previously joined `largecap_collection_state._id` to `companies._id`. The SEC CIK sync preserved legacy company profile `_id` values, so this join could exclude valid companies. ALL now enumerates tracked company profiles by ticker.
2. `repair_company` previously assumed `company._id` was the CIK. It now uses the synchronized `companies.cik` field, and queries financial records using integer and string CIK representations.
3. Existing balance sheet discrepancies are explicitly included in repair details with both stored and normalized SEC candidate residuals. Existing non-null values remain REVIEW ONLY.
4. The repair workflow now runs a full-universe dry-run by default, with optional guarded writes for validated *missing* fields only.
5. Derived liabilities from balance sheet arithmetic are not independently verified and are held for review.

## Safety and limitations

- Default mode is read-only. APPLY never overwrites non-null metrics and does not delete records.
- This release does not claim to automatically correct 442 reconciliation issues, create missing periods, or reconstruct unreported EPS. It generates evidence for each company's SEC data.
- Historical wrong-issuer CIK 0002115436 is flagged by the identity audit; no automatic deletion or migration is performed.
- SEC rate limits and free-tier MongoDB quotas may make 500-company review lengthy. Use a pilot before ALL.
- The SEC normalizer only consumes recognized us-gaap/dei facts; company-specific extensions require further source review.

## Suggested commit
`fix(v4.3.2.6): repair all-company CIK joins and audit SEC financial conflicts safely`
