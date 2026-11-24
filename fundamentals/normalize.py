"""v4.1.2: SEC Company Facts normalization using fiscal periods and filing provenance.

Only direct-duration quarterly values are emitted; cumulative YTD values are not
misrepresented as standalone quarters. Missing values remain missing.
"""
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
                        if is_quarter and not 70<=days<=110:continue
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
