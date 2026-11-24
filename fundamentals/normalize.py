"""v4.1.6: SEC normalization with traceable standalone quarterly cash flows."""
from datetime import date

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

def normalize(payload,years=5,today=None):
    if years < 1: raise ValueError('years must be positive')
    today=today or date.today()
    cutoff=date(today.year-years,today.month,min(today.day,28))
    facts=payload.get('facts') or {}
    gaap=facts.get('us-gaap') or {}
    dei=facts.get('dei') or {}
    if not isinstance(gaap,dict) or not isinstance(dei,dict):
        raise ValueError('Invalid SEC facts')
    rows={}
    cumulative={}  # (metric, fiscal year, quarter): most recent eligible YTD observation
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
                    fy=int(item['fy'])
                    fp=str(item['fp']).upper()
                    if fp not in ('FY','Q1','Q2','Q3','Q4'):continue
                    is_annual=form.startswith('10-K') and fp=='FY'
                    is_quarter=form.startswith('10-Q') and fp in ('Q1','Q2','Q3')
                    # SEC 10-K annual and 10-Q quarterly. A Q4 standalone value
                    # must be explicitly derived and validated; do not fabricate it.
                    if not (is_annual or is_quarter):continue
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
                                    ckey=(metric,fy,fp)
                                    candidate=(filed.toordinal(),-rank,item['val'],{
                                        'tag':tag,'filed':filed.isoformat(),'form':form,
                                        'accession':item.get('accn'),'start':start,
                                        'end':end.isoformat(),'fiscal_year':fy,'fiscal_period':fp
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
                            'fiscal_year':fy,'fiscal_period':fp
                        }
                except (KeyError,ValueError,TypeError,OverflowError):
                    continue
    # A cumulative-only quarter may have no other reported standalone facts.
    for (metric,fy,fp),entry in cumulative.items():
        end=entry[3]['end']; key=('quarterly',end)
        rows.setdefault(key,{'period':f'FY{fy}{fp}','fiscal_year':fy,'fiscal_period':fp,
            'period_end':end,'period_type':'quarterly','metrics':{},
            'metric_sources':{},'_priorities':{}})

    # Derive standalone Q2/Q3 from matching YTD facts. Q1 is already a
    # standalone three-month value. Q4 = FY - Q3 YTD, where both are present.
    # Never subtract across different fiscal years or unrelated fiscal starts.
    for row in rows.values():
        if row['period_type']!='quarterly':continue
        fp=row['fiscal_period']; fy=row['fiscal_year']
        if fp not in ('Q2','Q3'):continue
        for metric in ('operating_cash_flow','capex'):
            if metric in row['metrics']:continue
            current=cumulative.get((metric,fy,fp))
            previous_fp='Q1' if fp=='Q2' else 'Q2'
            previous=cumulative.get((metric,fy,previous_fp)) if fp=='Q3' else None
            if fp=='Q2':
                previous=next(( (None,None,r['metrics'][metric],r['metric_sources'][metric])
                    for r in rows.values() if r['period_type']=='quarterly' and r['fiscal_year']==fy
                    and r['fiscal_period']=='Q1' and metric in r['metrics']),None)
            if not current or not previous:continue
            src1,src0=current[3],previous[3]
            if src1.get('start')!=src0.get('start') and fp=='Q3':continue
            # Q2 cumulative start should match Q1 standalone start.
            if fp=='Q2' and src1.get('start')!=src0.get('start'):continue
            if not src1.get('end') or not src0.get('end') or src0['end']>=src1['end']:continue
            row['metrics'][metric]=current[2]-previous[2]
            row['metric_sources'][metric]={'method':'ytd_difference','current':src1,'previous':src0}

    # Q4: only derive if annual and Q3 YTD observations are compatible.
    for annual in [r for r in rows.values() if r['period_type']=='annual']:
        fy=annual['fiscal_year']
        q3=next((r for r in rows.values() if r['period_type']=='quarterly'
                 and r['fiscal_year']==fy and r['fiscal_period']=='Q3'),None)
        if not q3:continue
        q4_metrics={}; q4_sources={}
        for metric in ('operating_cash_flow','capex'):
            full=annual['metric_sources'].get(metric)
            ytd=cumulative.get((metric,fy,'Q3'))
            if not full or not ytd or full.get('start')!=ytd[3].get('start'):continue
            if not (ytd[3]['end']<annual['period_end']):continue
            q4_metrics[metric]=annual['metrics'][metric]-ytd[2]
            q4_sources[metric]={'method':'annual_minus_q3_ytd','annual':full,'q3_ytd':ytd[3]}
        if q4_metrics:
            # Do not manufacture a Q4 record containing only cash flows:
            # Q4 period-end is known, but its other statement metrics are not.
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
