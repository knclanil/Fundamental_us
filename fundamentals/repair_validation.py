"""v4.3.1 fail-closed validation of proposed SEC financial repairs."""
from datetime import date
from math import isfinite
from .quality_audit import reconcile

ADDITIVE={'revenue','gross_profit','operating_income','net_income'}
INSTANT={'assets','liabilities','equity','cash','current_assets','current_liabilities','long_term_debt','short_term_debt','shares'}

def _date(s):
    try: return date.fromisoformat(s)
    except (TypeError,ValueError): return None

def _number(v):
    return isinstance(v,(int,float)) and not isinstance(v,bool) and isfinite(v)

def validate(old, candidate, additions):
    """Return (approved, decisions); REVIEW/FAIL values are never writable."""
    approved={}; decisions={}
    for metric,item in additions.items():
        value=item['value']; src=item['source']; why=None; status='PASS'
        if not _number(value): status,why='FAIL','nonfinite_or_non_numeric'
        elif old.get('period_type') != candidate.get('period_type') or old.get('period_end') != candidate.get('period_end') or old.get('fiscal_year') != candidate.get('fiscal_year'):
            status,why='FAIL','period_identity_mismatch'
        elif old.get('fiscal_period') and candidate.get('fiscal_period') and old['fiscal_period'] != candidate['fiscal_period']:
            status,why='FAIL','fiscal_quarter_mismatch'
        elif not isinstance(src,dict): status,why='FAIL','missing_provenance'
        elif src.get('method')=='annual_minus_q1_q2_q3':
            annual=src.get('annual') or {}; quarters=src.get('quarters') or {}
            if metric not in ADDITIVE or old.get('fiscal_period')!='Q4': status,why='FAIL','unsupported_q4_derivation'
            elif set(quarters)!= {'Q1','Q2','Q3'}: status,why='FAIL','missing_quarter_sources'
            else:
                refs=[annual]+[quarters[q] for q in ('Q1','Q2','Q3')]
                if not all(isinstance(r,dict) for r in refs):
                    decisions[metric]=('FAIL','invalid_source_reference')
                    continue
                ends=[_date(r.get('end')) for r in refs]
                starts=[_date(r.get('start')) for r in refs]
                tags=[r.get('tag') for r in refs]
                if not all(isinstance(r,dict) for r in refs) or not all(ends) or not all(starts):status,why='FAIL','invalid_source_dates'
                elif not tags[0] or len(set(tags))!=1:status,why='FAIL','source_tag_mismatch'
                elif ends[0]!=_date(old.get('period_end')) or not (ends[1]<ends[2]<ends[3]<ends[0]):status,why='FAIL','source_period_mismatch'
                elif not 330 <= (ends[0]-starts[0]).days+1 <= 380 or any(not 70 <= (e-s).days+1 <= 110 for s,e in zip(starts[1:],ends[1:])):status,why='FAIL','invalid_duration'
                elif any(not r.get('accession') for r in refs):status,why='REVIEW','missing_accession'
        elif src.get('method')=='fiscal_year_end_snapshot':
            annual=src.get('annual') or {}
            if metric not in INSTANT or old.get('fiscal_period')!='Q4':status,why='FAIL','unsupported_snapshot'
            elif annual.get('end')!=old.get('period_end') or annual.get('start') is not None:status,why='FAIL','snapshot_date_mismatch'
            elif not annual.get('tag') or not annual.get('accession'):status,why='REVIEW','incomplete_source_reference'
        else:
            if not src.get('tag') or src.get('end')!=old.get('period_end') or not src.get('accession'):
                status,why='REVIEW','unverified_direct_source'
            elif src.get('start') and old.get('period_type')=='quarterly':
                start,end=_date(src['start']),_date(src['end'])
                if not start or not end or not 70 <= (end-start).days+1 <= 110:status,why='REVIEW','not_standalone_quarter'
        decisions[metric]=(status,why or 'validated')
        if status=='PASS':approved[metric]=item
    # Validate the combined balance-sheet additions, not each independently.
    combined=dict(old.get('metrics') or {})
    combined.update({k:item['value'] for k,item in approved.items()})
    trio=('assets','liabilities','equity')
    if any(k in approved for k in trio) and all(_number(combined.get(k)) for k in trio):
        after=reconcile([{'period_end':old.get('period_end'),'metrics':combined}])
        before=reconcile([{'period_end':old.get('period_end'),'metrics':old.get('metrics') or {}}]) if all(_number((old.get('metrics') or {}).get(k)) for k in trio) else []
        if after and (not before or abs(after[0]['residual']) >= abs(before[0]['residual'])):
            for k in trio:
                if k in approved: approved.pop(k);decisions[k]=('REVIEW','balance_sheet_unreconciled')
    return approved,decisions
