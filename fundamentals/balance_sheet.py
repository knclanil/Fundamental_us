"""v4.3.2.9: non-destructive balance-sheet enrichment and diagnostics."""
from math import isfinite

def number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and isfinite(x)

def assess(m):
    a=m.get('assets'); l=m.get('liabilities'); e=m.get('equity')
    ei=m.get('equity_including_nci'); n=m.get('noncontrolling_interest')
    r=m.get('redeemable_nci')
    if not number(a) or a<=0 or not number(l):
        return {'status':'insufficient_data'}
    if number(ei): total_equity=ei
    elif number(e): total_equity=e+(n if number(n) else 0)
    else: return {'status':'insufficient_data'}
    claims=l+total_equity+(r if number(r) else 0)
    ratio=abs(claims/a)
    residual=a-claims
    return {'status':'scale_outlier' if ratio>10 else ('reconciled' if abs(residual)/a<=.02 else 'unreconciled'),
            'residual':residual,'relative_difference':abs(residual)/a,'claims_to_assets':ratio}

def reconciliation_diagnostics(metrics, sources=None):
    """Read-only, source-aware reconciliation alternatives; never mutate SEC facts.

    Alternative equations are hypotheses, not permission to repair stored values.
    """
    m = metrics or {}
    sources = sources or {}
    base = assess(m)
    out = {'reported': base, 'alternatives': [], 'source_review': {}}
    for key in ('assets', 'liabilities', 'equity', 'equity_including_nci',
                'noncontrolling_interest', 'redeemable_nci',
                'liabilities_and_stockholders_equity'):
        src = sources.get(key)
        if src is not None:
            out['source_review'][key] = src
    a, l = m.get('assets'), m.get('liabilities')
    if not (number(a) and a > 0 and number(l)):
        return out
    candidates = []
    e, ei, n, r = (m.get(k) for k in ('equity','equity_including_nci',
                                     'noncontrolling_interest','redeemable_nci'))
    if number(e):
        candidates.append(('parent_equity_only', l + e))
        if number(n):
            candidates.append(('parent_equity_plus_nci', l + e + n))
    if number(ei):
        candidates.append(('equity_including_nci', l + ei))
    if number(r) and number(ei):
        candidates.append(('equity_including_nci_plus_redeemable', l + ei + r))
    combined = m.get('liabilities_and_stockholders_equity')
    if number(combined):
        candidates.append(('sec_reported_liabilities_and_equity_total', combined))
    for label, claims in candidates:
        residual = a - claims
        out['alternatives'].append({'equation':label,'residual':residual,
                                    'relative_difference':abs(residual)/a,
                                    'within_tolerance':abs(residual)/a <= .02})
    out['review_required'] = base['status'] in ('unreconciled','scale_outlier')
    return out


def enrich_balance_sheet(m, sources=None):
    """Only fill absent liabilities; never overwrite SEC-reported liabilities.

    An asset-equity residual alone is NOT independent evidence of liabilities;
    it is retained as a review candidate, not silently accepted.
    """
    sources=sources if sources is not None else {}
    if m.get('liabilities') is None:
        c=m.get('current_liabilities'); nc=m.get('liabilities_noncurrent')
        combined=m.get('liabilities_and_stockholders_equity')
        ei=m.get('equity_including_nci'); e=m.get('equity')
        n=m.get('noncontrolling_interest'); r=m.get('redeemable_nci')
        eq=ei if number(ei) else e+(n if number(n) else 0) if number(e) else None
        redeem=r if number(r) else 0
        candidate=None; method=None; inputs=[]
        if number(c) and number(nc):
            candidate=c+nc;method='current_plus_noncurrent';inputs=['current_liabilities','liabilities_noncurrent']
        elif number(combined) and number(eq):
            candidate=combined-eq-redeem;method='combined_minus_equity';inputs=['liabilities_and_stockholders_equity','equity_including_nci' if number(ei) else 'equity']
        elif number(m.get('assets')) and number(eq):
            candidate=m['assets']-eq-redeem;method='assets_minus_equity';inputs=['assets','equity_including_nci' if number(ei) else 'equity']
        if candidate is not None and number(candidate) and candidate>=0:
            trial={**m,'liabilities':candidate}
            check=assess(trial)
            # Reject extreme scales; for residual-based derivation, avoid
            # treating arithmetic tautology as independent verification.
            if check['status']!='scale_outlier':
                if method=='assets_minus_equity':
                    m['liabilities_derivation_candidate']=candidate
                    sources['liabilities_derivation_candidate']={'method':method,'review_required':True,'inputs':inputs}
                else:
                    m['liabilities']=candidate
                    sources['liabilities']={'method':method,'inputs':inputs,'derived':True,'review_required':check['status']=='unreconciled'}
    result=assess(m)
    if result['status']!='insufficient_data':
        m['reconciliation_residual']=result['residual']
        m['is_balance_sheet_reconciled']=result['status']=='reconciled'
        if result['status']=='scale_outlier':m['scale_error']=True
    return result
