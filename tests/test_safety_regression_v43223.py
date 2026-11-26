"""Offline safety regressions for SEC balance-sheet alignment."""
from copy import deepcopy
from datetime import date
from fundamentals.fact_alignment import align_balance_sheet

END='2023-10-31'

def row(metrics, period_type='annual'):
    return {'period_end':END,'period_type':period_type,'metrics':dict(metrics),'metric_sources':{}}

def facts(values, accession='x', form='10-K', end=END, filed=date(2024,12,20)):
    return [{'metric':k,'tag':k,'val':v,'end':end,'filed':filed,'form':form,'accn':accession,'rank':0} for k,v in values.items()]

def test_already_reconciled_is_not_changed():
    r=row({'assets':100,'liabilities':40,'equity':60}); old=deepcopy(r)
    assert not align_balance_sheet(r,facts({'assets':200,'liabilities':50,'equity':150}))
    assert r==old

def test_no_matching_period_is_not_changed():
    r=row({'assets':100,'liabilities':40,'equity':600}); old=deepcopy(r)
    assert not align_balance_sheet(r,facts({'assets':100,'liabilities':40,'equity':60},end='2022-10-31'))
    assert r==old

def test_no_matching_form_is_not_changed():
    r=row({'assets':100,'liabilities':40,'equity':600}); old=deepcopy(r)
    assert not align_balance_sheet(r,facts({'assets':100,'liabilities':40,'equity':60},form='10-Q'))
    assert r==old

def test_no_cross_accession_assembly():
    r=row({'assets':100,'liabilities':40,'equity':600}); old=deepcopy(r)
    observations=facts({'assets':100,'liabilities':40},accession='one')+facts({'equity':60},accession='two')
    assert not align_balance_sheet(r,observations)
    assert r==old

def test_incomplete_candidate_not_accepted():
    r=row({'assets':100,'liabilities':40,'equity':600}); old=deepcopy(r)
    assert not align_balance_sheet(r,facts({'assets':100,'liabilities':40}))
    assert r==old

def test_noncontrolling_interest_can_reconcile():
    r=row({'assets':100,'liabilities':40,'equity':600})
    assert align_balance_sheet(r,facts({'assets':100,'liabilities':40,'equity':55,'noncontrolling_interest':5}))
    assert r['metrics']['noncontrolling_interest']==5

def test_quarterly_requires_ten_q():
    r=row({'assets':100,'liabilities':40,'equity':600},period_type='quarterly')
    assert align_balance_sheet(r,facts({'assets':100,'liabilities':40,'equity':60},form='10-Q'))

def test_repeated_alignment_is_idempotent():
    r=row({'assets':100,'liabilities':40,'equity':600})
    obs=facts({'assets':100,'liabilities':40,'equity':60})
    assert align_balance_sheet(r,obs)
    snapshot=deepcopy(r)
    assert not align_balance_sheet(r,obs)
    assert r==snapshot

def test_unreconciled_candidate_not_accepted():
    r=row({'assets':100,'liabilities':40,'equity':600}); old=deepcopy(r)
    assert not align_balance_sheet(r,facts({'assets':100,'liabilities':40,'equity':50}))
    assert r==old

def test_sources_include_accession_and_method():
    r=row({'assets':100,'liabilities':40,'equity':600})
    assert align_balance_sheet(r,facts({'assets':100,'liabilities':40,'equity':60},accession='abc'))
    for k in ('assets','liabilities','equity'):
        assert r['metric_sources'][k]['accession']=='abc'
        assert r['metric_sources'][k]['method']=='single_accession_balance_sheet_alignment'
