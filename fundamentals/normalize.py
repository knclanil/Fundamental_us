"""SEC XBRL normalization; periods are identified by filing frame and form."""
from datetime import date, timedelta

TAGS = {
 'revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet','RevenueFromContractWithCustomerIncludingAssessedTax'],
 'gross_profit':['GrossProfit'], 'operating_income':['OperatingIncomeLoss'],
 'net_income':['NetIncomeLoss','ProfitLoss'], 'eps_basic':['EarningsPerShareBasic'],
 'eps_diluted':['EarningsPerShareDiluted'], 'assets':['Assets'],
 'liabilities':['Liabilities'], 'equity':['StockholdersEquity','StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],
 'cash':['CashAndCashEquivalentsAtCarryingValue'], 'current_assets':['AssetsCurrent'],
 'current_liabilities':['LiabilitiesCurrent'], 'long_term_debt':['LongTermDebtCurrent','LongTermDebtNoncurrent','LongTermDebt'],
 'operating_cash_flow':['NetCashProvidedByUsedInOperatingActivities'],
 'capex':['PaymentsToAcquirePropertyPlantAndEquipment'],
 'shares':['CommonStockSharesOutstanding']
}
UNIT = {'eps_basic':'USD/shares','eps_diluted':'USD/shares','shares':'shares'}
BALANCE = {'assets','liabilities','equity','cash','current_assets','current_liabilities','long_term_debt','shares'}

def normalize(payload, years=5, today=None):
    if years < 1: raise ValueError('years must be positive')
    today = today or date.today()
    cutoff = date(today.year-years, today.month, min(today.day, 28))
    gaap = payload.get('facts',{}).get('us-gaap',{})
    dei = payload.get('facts',{}).get('dei',{})
    if not isinstance(gaap,dict): raise ValueError('Invalid SEC facts')
    output = {}
    for metric, tags in TAGS.items():
        for tag in tags:
            fact = gaap.get(tag) or (dei.get(tag) if metric=='shares' else None)
            if not fact: continue
            entries = fact.get('units',{}).get(UNIT.get(metric,'USD'),[])
            for item in entries:
                try:
                    end = date.fromisoformat(item['end']); filed = date.fromisoformat(item['filed'])
                    if not cutoff <= end <= today or filed > today: continue
                    form = item.get('form','')
                    if form not in ('10-K','10-Q','10-K/A','10-Q/A'): continue
                    frame = item.get('frame','')
                    if not frame or not frame.startswith('CY'): continue
                    is_quarter = 'Q' in frame
                    # Require a distinct frame: avoids double counting year-to-date cash flows.
                    if ('I' in frame) != (metric in BALANCE): continue
                    kind = 'quarterly' if is_quarter else 'annual'
                    if metric not in BALANCE and not item.get('start'): continue
                    if metric in BALANCE and item.get('start'): continue
                    key = (kind, frame)
                    current = output.setdefault(key, {'period':frame,'period_end':end.isoformat(),'period_type':kind,'metrics':{},'_source':{}})
                    prev = current['_source'].get(metric)
                    priority = (filed.isoformat(), -tags.index(tag))
                    if prev is None or priority > prev:
                        current['metrics'][metric] = item['val']
                        current['_source'][metric] = priority
                except (KeyError,TypeError,ValueError):
                    continue
    rows = []
    for row in output.values():
        row.pop('_source')
        m = row['metrics']
        if 'operating_cash_flow' in m and 'capex' in m:
            m['free_cash_flow'] = m['operating_cash_flow'] - abs(m['capex'])
        rows.append(row)
    return sorted(rows,key=lambda x:(x['period_end'],x['period_type'],x['period']))
