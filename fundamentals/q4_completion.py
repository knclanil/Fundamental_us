"""v4.2.2: conservative, source-aware Q4 completion; no EPS estimation."""
from datetime import date

ADDITIVE = ('revenue', 'gross_profit', 'operating_income', 'net_income')
INSTANT = ('assets', 'liabilities', 'equity', 'cash', 'current_assets',
           'current_liabilities', 'long_term_debt', 'short_term_debt', 'shares')


def complete_q4(annual, quarters):
    """Return missing Q4 metric values and provenance, never mutate inputs.

    Annual and Q1-Q3 must share fiscal year, valid chronological quarter ends,
    and an annual year-end matching the Q4 document. Subtraction is performed
    only when all three standalone quarter observations exist. EPS is excluded:
    annual and quarterly weighted-average denominators are not additive.
    """
    fy=annual.get('fiscal_year')
    end=annual.get('period_end')
    if annual.get('period_type')!='annual' or not fy or not end:
        return {}, {}
    try: annual_end=date.fromisoformat(end)
    except (ValueError,TypeError): return {}, {}
    qmap={}
    for q in quarters:
        if q.get('fiscal_year')!=fy or q.get('period_type')!='quarterly': continue
        fp=q.get('fiscal_period')
        if fp not in ('Q1','Q2','Q3'):continue
        if fp in qmap:return {}, {}  # ambiguous fiscal periods: fail closed
        qmap[fp]=q
    if set(qmap)!=set(('Q1','Q2','Q3')):return {}, {}
    try:
        dates=[date.fromisoformat(qmap[k]['period_end']) for k in ('Q1','Q2','Q3')]
    except (KeyError,ValueError,TypeError):return {}, {}
    if not (dates[0]<dates[1]<dates[2]<annual_end):return {}, {}
    if not all(70 <= (b-a).days <= 110 for a,b in zip(dates,dates[1:]+[annual_end])):
        return {}, {}
    am=annual.get('metrics') or {}; sources=annual.get('metric_sources') or {}
    out={}; provenance={}
    for metric in ADDITIVE:
        values=[(qmap[k].get('metrics') or {}).get(metric) for k in ('Q1','Q2','Q3')]
        full=am.get(metric)
        if not all(isinstance(v,(int,float)) and not isinstance(v,bool) for v in [full,*values]):continue
        # Require SEC-derived source metadata for every operand.
        refs=[(qmap[k].get('metric_sources') or {}).get(metric) for k in ('Q1','Q2','Q3')]
        annual_src=sources.get(metric)
        if not annual_src or any(not r for r in refs):continue
        # Source tags must match; different accounting concepts must not be subtracted.
        tags=[r.get('tag') for r in [annual_src,*refs]]
        if not tags[0] or len(set(tags))!=1:continue
        # SEC duration facts must actually end at their corresponding quarter end.
        if annual_src.get('end')!=end or any(r.get('end')!=qmap[k]['period_end'] for r,k in zip(refs,('Q1','Q2','Q3'))):continue
        # Q1-Q3 must be standalone ~3 month observations, not YTD.
        try:
            if any(not 70 <= (date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days+1 <= 110 for r in refs):continue
            if not 330 <= (annual_end-date.fromisoformat(annual_src['start'])).days+1 <= 380:continue
        except (KeyError,ValueError,TypeError):continue
        value=full-sum(values)
        if value < 0 and metric in ('revenue','gross_profit'):continue
        out[metric]=value
        provenance[metric]={'method':'annual_minus_q1_q2_q3', 'annual':annual_src,
                            'quarters':{k:r for k,r in zip(('Q1','Q2','Q3'),refs)}}
    for metric in INSTANT:
        val=am.get(metric); src=sources.get(metric)
        if not isinstance(val,(int,float)) or isinstance(val,bool) or not src:continue
        if src.get('end')!=end or src.get('start') is not None:continue
        out[metric]=val
        provenance[metric]={'method':'fiscal_year_end_snapshot','annual':src}
    return out,provenance
