"""Conservative SEC instant-fact alignment for balance-sheet statements.

Only replace a mixed-filing combination with facts from ONE actual accession,
for the same reporting end date, when the accounting identity improves.
"""
from datetime import date
from math import isfinite

KEYS = ('assets', 'liabilities', 'equity', 'equity_including_nci',
        'noncontrolling_interest', 'redeemable_nci')

def align_balance_sheet(row, observations):
    metrics = row['metrics']; sources = row['metric_sources']
    end = row['period_end']
    relevant = [x for x in observations if x['end'] == end and x['metric'] in KEYS
                and x.get('accn') and x.get('form') == ('10-K' if row['period_type']=='annual' else '10-Q')]
    by_accession = {}
    for x in relevant:
        group = by_accession.setdefault(x['accn'], {})
        old = group.get(x['metric'])
        if old is None or (x['filed'], -x['rank']) > (old['filed'], -old['rank']):
            group[x['metric']] = x

    def score(m):
        a, l = m.get('assets'), m.get('liabilities')
        e = m.get('equity_including_nci')
        if e is None:
            e = m.get('equity')
            if e is not None: e += m.get('noncontrolling_interest') or 0
        if any(not isinstance(v, (float, int)) or not isfinite(v) for v in (a,l,e)) or a <= 0:
            return None
        return abs(a-l-e-(m.get('redeemable_nci') or 0))/a

    original = score(metrics)
    if original is None or original <= .02: return False
    candidates = []
    for accn, facts in by_accession.items():
        if not {'assets','liabilities'} <= facts.keys(): continue
        if not ('equity_including_nci' in facts or 'equity' in facts): continue
        proposed = dict(metrics)
        # Never mix parent equity with NCI from a different filing.
        for k in KEYS: proposed.pop(k, None)
        for k, fact in facts.items(): proposed[k] = fact['val']
        s = score(proposed)
        if s is not None and s <= .02 and s < original:
            candidates.append((s, -max(x['filed'] for x in facts.values()).toordinal(), accn, proposed, facts))
    if not candidates: return False
    _, _, accn, proposed, facts = min(candidates, key=lambda x:(x[0],x[1],x[2]))
    for k in KEYS:
        metrics.pop(k,None); sources.pop(k,None)
    for k, fact in facts.items():
        metrics[k] = fact['val']
        sources[k] = {'tag':fact['tag'],'filed':fact['filed'].isoformat(),
                      'form':fact['form'],'accession':accn,'end':end,
                      'method':'single_accession_balance_sheet_alignment',
                      'context_dimensions_verified':False}
    row['balance_sheet_alignment'] = {'method':'single_accession', 'accession':accn,
                                      'original_relative_difference':original,
                                      'new_relative_difference':score(proposed)}
    return True
