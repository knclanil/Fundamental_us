"""v4.3.2.8: dimension-aware, source-traceable balance sheet normalization.

Use filing-level XBRL facts for dimension filtering. SEC companyfacts does not
expose complete segment/context dimensions: absence of 'segment' there is NOT
proof that a fact is dimensionless. Never auto-apply corrections from this module.
"""
from math import isfinite, log10


def valid(fact, *, allow_class=False):
    """Only accept explicitly known dimensionless filing-level observations."""
    if not fact.get('dimensions_verified', False):
        return False
    dims = fact.get('dimensions', fact.get('segment'))
    if not dims:
        return True
    if allow_class and isinstance(dims, dict) and len(dims) == 1:
        return next(iter(dims)).split(':')[-1] == 'StatementClassOfStockAxis'
    return False


def choose(facts, tag, end, accession, *, allow_class=False, primary_class=None):
    eligible = [f for f in facts if f.get('tag', '').split(':')[-1] == tag
                and f.get('end') == end and f.get('accession') == accession
                and valid(f, allow_class=allow_class) and f.get('unit') in ('USD', 'USD/shares')]
    if allow_class and primary_class:
        eligible = [f for f in eligible if not f.get('dimensions') or
                    primary_class in str(f.get('dimensions'))]
    # Ambiguous contexts must be reviewed, not silently picked.
    values = {f.get('value') for f in eligible if isinstance(f.get('value'), (int, float))}
    return next(iter(values)) if len(values) == 1 else None


def balance(facts, end, accession):
    def get(tag):
        return choose(facts, tag, end, accession)
    a = get('Assets')
    combined = get('LiabilitiesAndStockholdersEquity')
    parent = get('StockholdersEquity')
    nci = get('MinorityInterest')
    total = get('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest')
    if total is None and parent is not None:
        total = parent + (nci if nci is not None else 0)
    # Redeemable / temporary equity is often outside permanent equity. Do NOT
    # fold it into total_equity; model it separately as a claim on assets.
    redeemable = get('RedeemableNoncontrollingInterestEquityCarryingAmount')
    if redeemable is None:
        redeemable = get('TemporaryEquityCarryingAmountAttributableParent')
    l = get('Liabilities')
    method = 'direct'
    if l is None:
        cur, noncur = get('LiabilitiesCurrent'), get('LiabilitiesNoncurrent')
        if cur is not None and noncur is not None:
            l, method = cur + noncur, 'current_plus_noncurrent'
        elif combined is not None and total is not None:
            l, method = combined - total - (redeemable or 0), 'combined_minus_equity_review'
    residual = None if a is None or l is None or total is None else a - l - total - (redeemable or 0)
    tolerance = None if a is None else max(1_000_000, .005 * abs(a))
    return {'total_assets': a, 'liabilities_and_equity': combined,
            'stockholders_equity_parent': parent, 'noncontrolling_interest': nci,
            'total_equity': total, 'redeemable_equity_separate': redeemable,
            'total_liabilities': l, 'liabilities_method': method,
            'discrepancy': residual, 'tolerance': tolerance,
            'reconciled': residual is not None and abs(residual) <= tolerance,
            'review_required': method != 'direct' or redeemable is not None}


def diluted_eps(facts, end, accession, *, start=None, primary_class=None):
    """Duration-aware EPS; never mix different start dates or accessions."""
    relevant = [f for f in facts if f.get('start') == start and f.get('unit') == 'USD/shares']
    get = lambda tag, allow=False: choose(relevant, tag, end, accession,
                                          allow_class=allow, primary_class=primary_class)
    direct = get('EarningsPerShareDiluted')
    if direct is not None:
        return direct, 'direct'
    continuing = get('IncomeLossFromContinuingOperationsPerDilutedShare')
    if continuing is not None:
        return continuing + (get('IncomeLossFromDiscontinuedOperationsNetOfTaxPerDilutedShare') or 0), 'components_review'
    if primary_class:
        candidate = get('EarningsPerShareDiluted', True)
        if candidate is not None:
            return candidate, 'primary_class_review'
    return None, 'missing'


def scale_candidate(current, previous, *, adjacent_next=None):
    """Flag a possible scale jump; never auto-correct from ratios alone."""
    if not all(isinstance(v, (int, float)) and isfinite(v) and v > 0
               for v in (current, previous)):
        return None
    ratio = current / previous
    for factor in (1e3, 1e6, 1e-3, 1e-6):
        if abs(log10(ratio / factor)) <= .1:
            return {'suspected_factor': factor, 'review_required': True,
                    'reason': 'Adjacent-period ratios alone cannot prove XBRL unit scaling'}
    return None
