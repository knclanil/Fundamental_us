"""v4.1.9: fiscal calendar inference with sparse-fact fixture support."""
from datetime import date, timedelta
import calendar

TAGS = {
    'revenue': ['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet','RevenueFromContractWithCustomerIncludingAssessedTax'],
    'gross_profit':['GrossProfit'], 'operating_income':['OperatingIncomeLoss'],
    'net_income':['NetIncomeLoss','ProfitLoss'],
    'eps_basic':['EarningsPerShareBasic'], 'eps_diluted':['EarningsPerShareDiluted'],
    'assets':['Assets'], 'liabilities':['Liabilities'],
    'equity':['StockholdersEquity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],
    'cash':['CashAndCashEquivalentsAtCarryingValue'],
    'current_assets':['AssetsCurrent'], 'current_liabilities':['LiabilitiesCurrent'],
    'long_term_debt':['LongTermDebtNoncurrent','LongTermDebt'],
    'short_term_debt':['LongTermDebtCurrent','ShortTermBorrowings'],
    'operating_cash_flow':['NetCashProvidedByUsedInOperatingActivities'],
    'capex':['PaymentsToAcquirePropertyPlantAndEquipment'],
    'shares':['CommonStockSharesOutstanding']
}
UNITS={'eps_basic':'USD/shares','eps_diluted':'USD/shares','shares':'shares'}
INSTANT={'assets','liabilities','equity','cash','current_assets','current_liabilities','long_term_debt','short_term_debt','shares'}
FORMS={'10-K','10-K/A','10-Q','10-Q/A'}

def _shift_months(day, months):
    index = day.year * 12 + day.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def _fiscal_calendar(gaap, today):
    """Infer fiscal year ends from actual annual-duration 10-K facts, not SEC fy/fp.

    A historical 10-Q comparative snapshot is never a fiscal-quarter anchor.
    """
    ends = []
    for tag in ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax',
                'NetIncomeLoss', 'OperatingIncomeLoss'):
        for obs in (gaap.get(tag) or {}).get('units', {}).get('USD', []):
            try:
                end = date.fromisoformat(obs['end'])
                start = date.fromisoformat(obs['start'])
                filed = date.fromisoformat(obs['filed'])
                if (obs.get('form') in ('10-K', '10-K/A') and
                        330 <= (end-start).days+1 <= 380 and filed <= today and end <= today):
                    ends.append(end)
            except (ValueError, TypeError, KeyError):
                continue
    if not ends:
        # A Q1 3-month duration is a safe fiscal calendar anchor when no
        # annual duration is available in a synthetic or sparse payload.
        for tag in ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax',
                    'NetIncomeLoss', 'OperatingIncomeLoss',
                    'NetCashProvidedByUsedInOperatingActivities'):
            for obs in (gaap.get(tag) or {}).get('units', {}).get('USD', []):
                try:
                    start=date.fromisoformat(obs['start']); end=date.fromisoformat(obs['end'])
                    if (obs.get('form') in ('10-Q','10-Q/A') and
                        obs.get('fp')=='Q1' and 70 <= (end-start).days+1 <= 110):
                        ends.append(_shift_months(end,9))
                except (KeyError,ValueError,TypeError):continue
    if not ends:
        # A verified three-month Q3 income statement anchors the year end.
        for tag in ('Revenues', 'RevenueFromContractWithCustomerExcludingAssessedTax',
                    'NetIncomeLoss', 'OperatingIncomeLoss'):
            for obs in (gaap.get(tag) or {}).get('units', {}).get('USD', []):
                try:
                    start=date.fromisoformat(obs['start']); end=date.fromisoformat(obs['end'])
                    if (obs.get('form') in ('10-Q','10-Q/A') and
                        obs.get('fp')=='Q3' and 70 <= (end-start).days+1 <= 110):
                        ends.append(_shift_months(end,3))
                except (KeyError,ValueError,TypeError):continue
    if not ends:
        # Sparse Company Facts may contain only 10-K balance-sheet instants.
        # A 10-K FY snapshot is a fiscal year-end candidate; never infer
        # a quarter from a 10-Q comparative instant.
        for tag in ('Assets', 'Liabilities', 'StockholdersEquity'):
            for obs in (gaap.get(tag) or {}).get('units', {}).get('USD', []):
                try:
                    end=date.fromisoformat(obs['end'])
                    filed=date.fromisoformat(obs['filed'])
                    if (obs.get('form') in ('10-K','10-K/A') and
                            obs.get('fp')=='FY' and filed<=today and end<=today):
                        ends.append(end)
                except (KeyError, ValueError, TypeError):
                    continue
    if not ends:
        return None
    # Use the most recent annual end to establish the company's fiscal calendar.
    return max(ends)


def _actual_period(end, annual_anchor):
    """Return (FY, fiscal quarter), based on real period end and fiscal calendar.

    Allow small drift in quarter ends for 52/53-week reporting companies.
    """
    candidates = []
    for year in range(end.year-2, end.year+3):
        try:
            fy_end = annual_anchor.replace(year=year)
        except ValueError:
            fy_end = date(year, 2, 28)
        for quarter in range(1, 5):
            target = _shift_months(fy_end, -3 * (4-quarter))
            distance = abs((end-target).days)
            if distance <= 9:
                candidates.append((distance, year, quarter))
    if not candidates:
        return None
    _, year, quarter = min(candidates)
    return year, quarter

def normalize(payload,years=5,today=None):
    if years < 1: raise ValueError('years must be positive')
    today=today or date.today()
    cutoff=date(today.year-years,today.month,min(today.day,28))
    facts=payload.get('facts') or {}
    gaap=facts.get('us-gaap') or {}
    dei=facts.get('dei') or {}
    if not isinstance(gaap,dict) or not isinstance(dei,dict):
        raise ValueError('Invalid SEC facts')
    annual_anchor=_fiscal_calendar(gaap,today)
    rows={}
    cumulative={}  # (metric, actual YTD end date): latest eligible SEC YTD observation
    for metric,tags in TAGS.items():
        for rank,tag in enumerate(tags):
            fact=gaap.get(tag) or (dei.get(tag) if metric=='shares' else None)
            if not isinstance(fact,dict):continue
            for item in fact.get('units',{}).get(UNITS.get(metric,'USD'),[]):
                try:
                    end=date.fromisoformat(item['end'])
                    filed=date.fromisoformat(item['filed'])
                    form=item.get('form','')
                    if not cutoff<=end<=today or filed>today or form not in FORMS:continue
                    filing_fy=int(item['fy'])
                    filing_fp=str(item['fp']).upper()
                    actual=_actual_period(end,annual_anchor) if annual_anchor else None
                    if not actual:continue
                    fy,quarter=actual
                    fp='FY' if quarter==4 and form.startswith('10-K') else f'Q{quarter}'
                    if fp not in ('FY','Q1','Q2','Q3','Q4'):continue
                    is_annual=form.startswith('10-K') and quarter==4
                    is_quarter=form.startswith('10-Q') and quarter in (1,2,3)
                    # SEC 10-K annual and 10-Q quarterly. A Q4 standalone value
                    # must be explicitly derived and validated; do not fabricate it.
                    if not (is_annual or is_quarter):continue
                    # A 10-Q can repeat last year's year-end balance sheet.
                    # Its actual end date maps to Q4, so it is rejected above.
                    start=item.get('start')
                    if metric in INSTANT:
                        if start:continue
                    else:
                        if not start:continue
                        start_date=date.fromisoformat(start)
                        days=(end-start_date).days+1
                        if is_annual and not 330<=days<=380:continue
                        if is_quarter and not 70<=days<=110:
                            # Cash flow is generally reported year-to-date in 10-Q.
                            # Retain it for a DIFFERENCE, never as standalone cash flow.
                            if metric in ('operating_cash_flow','capex') and fp in ('Q2','Q3') and 140<=days<=300:
                                expected={'Q2':(140,210),'Q3':(230,300)}[fp]
                                if expected[0]<=days<=expected[1]:
                                    ckey=(metric,end.isoformat())
                                    candidate=(filed.toordinal(),-rank,item['val'],{
                                        'tag':tag,'filed':filed.isoformat(),'form':form,
                                        'accession':item.get('accn'),'start':start,
                                        'end':end.isoformat(),'fiscal_year':fy,'fiscal_period':fp,'filing_fy':filing_fy,'filing_fp':filing_fp
                                    })
                                    if candidate[:2]>(cumulative.get(ckey) or (-1,-999))[:2]:
                                        cumulative[ckey]=candidate
                            continue
                    kind='annual' if is_annual else 'quarterly'
                    label=f'FY{fy}' if is_annual else f'FY{fy}{fp}'
                    key=(kind,end.isoformat())
                    row=rows.setdefault(key,{
                        'period':label,'fiscal_year':fy,'fiscal_period':'FY' if is_annual else fp,
                        'period_end':end.isoformat(),'period_type':kind,'metrics':{},
                        'metric_sources':{},'_priorities':{}
                    })
                    priority=(filed.toordinal(),-rank)
                    if priority>row['_priorities'].get(metric,(-1,-999)):
                        row['metrics'][metric]=item['val']
                        row['_priorities'][metric]=priority
                        row['metric_sources'][metric]={
                            'tag':tag,'filed':filed.isoformat(),'form':form,
                            'accession':item.get('accn'),
                            'start':start,'end':end.isoformat(),
                            'fiscal_year':fy,'fiscal_period':fp,'filing_fy':filing_fy,'filing_fp':filing_fp
                        }
                except (KeyError,ValueError,TypeError,OverflowError):
                    continue
    # SEC fy/fp describes the FILING, not necessarily the fact's reporting year.
    # Never use fy/fp to associate cumulative cash flow with a target quarter.
    # Anchor all inputs to the actual reporting end dates of income-statement
    # quarter rows. Comparative prior-year observations must not be relabeled.
    quarter_rows=[r for r in rows.values() if r['period_type']=='quarterly'
                    and any(m in r['metrics'] for m in ('revenue','net_income','operating_income'))]
    for row in quarter_rows:
        fp=row['fiscal_period']
        if fp not in ('Q2','Q3'):continue
        fy=row['fiscal_year']
        prior_fp='Q1' if fp=='Q2' else 'Q2'
        # Select the actual previous fiscal quarter by its end date. SEC
        # comparative facts may have fy=2026 even when end=2025-09-30.
        candidates=[r for r in quarter_rows if r['fiscal_year']==fy
                    and r['fiscal_period']==prior_fp
                    and r['period_end']<row['period_end']]
        candidates=[r for r in candidates if 70 <=
                    (date.fromisoformat(row['period_end'])-date.fromisoformat(r['period_end'])).days <= 110]
        if len(candidates)!=1:continue
        prev_row=candidates[0]
        for metric in ('operating_cash_flow','capex'):
            if metric in row['metrics']:continue
            current=cumulative.get((metric,row['period_end']))
            if not current:continue
            src1=current[3]
            if fp=='Q2':
                if metric not in prev_row['metrics']:continue
                previous_value=prev_row['metrics'][metric]
                src0=prev_row['metric_sources'][metric]
            else:
                previous=cumulative.get((metric,prev_row['period_end']))
                if not previous:continue
                previous_value=previous[2];src0=previous[3]
            if src1.get('start')!=src0.get('start'):continue
            if src0.get('end')!=prev_row['period_end'] or src1.get('end')!=row['period_end']:continue
            start=date.fromisoformat(src1['start'])
            # Reject comparative values and unexpected fiscal durations.
            if not (140 <= (date.fromisoformat(src1['end'])-start).days+1 <= 300):continue
            if fp=='Q3' and not (230 <= (date.fromisoformat(src1['end'])-start).days+1 <= 300):continue
            row['metrics'][metric]=current[2]-previous_value
            row['metric_sources'][metric]={'method':'ytd_difference','current':src1,'previous':src0}

    # Q4 is derived only from annual data and an actual Q3 reporting period
    # whose end is approximately one quarter before the annual end.
    for annual in [r for r in rows.values() if r['period_type']=='annual']:
        fy=annual['fiscal_year']
        q3_candidates=[r for r in quarter_rows if r['fiscal_year']==fy
                       and r['fiscal_period']=='Q3' and 70 <=
                       (date.fromisoformat(annual['period_end'])-date.fromisoformat(r['period_end'])).days <= 110]
        if len(q3_candidates)!=1:continue
        q3=q3_candidates[0]
        q4_metrics={};q4_sources={}
        for metric in ('operating_cash_flow','capex'):
            full=annual['metric_sources'].get(metric)
            ytd=cumulative.get((metric,q3['period_end']))
            if not full or not ytd:continue
            if full.get('start')!=ytd[3].get('start'):continue
            if full.get('end')!=annual['period_end'] or ytd[3]['end']!=q3['period_end']:continue
            q4_metrics[metric]=annual['metrics'][metric]-ytd[2]
            q4_sources[metric]={'method':'annual_minus_q3_ytd','annual':full,'q3_ytd':ytd[3]}
        if q4_metrics:
            key=('quarterly',annual['period_end'])
            q4=rows.setdefault(key,{'period':f'FY{fy}Q4','fiscal_year':fy,'fiscal_period':'Q4',
                  'period_end':annual['period_end'],'period_type':'quarterly',
                  'metrics':{},'metric_sources':{},'_priorities':{}})
            for metric,value in q4_metrics.items():
                if metric not in q4['metrics']:
                    q4['metrics'][metric]=value;q4['metric_sources'][metric]=q4_sources[metric]
    result=[]
    for row in rows.values():
        row.pop('_priorities')
        m=row['metrics']
        if 'operating_cash_flow' in m and 'capex' in m:
            m['free_cash_flow']=m['operating_cash_flow']-abs(m['capex'])
        # A row with only an instant value is still valid; consumers can
        # inspect missing fields rather than treating them as zeros.
        if m:result.append(row)
    return sorted(result,key=lambda r:(r['period_end'],r['period_type']))
