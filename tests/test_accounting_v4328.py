import unittest
from fundamentals.accounting_v4328 import balance, diluted_eps, valid, scale_candidate

END='2023-10-31'; ACC='sample-accession'
def fact(tag, value, end=END, acc=ACC, **kw):
    return {'tag':tag,'value':value,'end':end,'accession':acc,
            'unit':'USD','dimensions_verified':True,**kw}

class AccountingTests(unittest.TestCase):
    def test_agilent_fixture(self):
        facts=[fact('Assets',10763e6),fact('Liabilities',4918e6),
               fact('StockholdersEquity',5845e6),
               fact('StockholdersEquity',-327e6,dimensions={'us-gaap:StatementEquityComponentsAxis':'AccumulatedOtherComprehensiveIncomeLossMember'})]
        r=balance(facts,END,ACC)
        self.assertEqual(r['total_equity'],5845e6)
        self.assertEqual(r['discrepancy'],0)
    def test_blackstone_fixture(self):
        facts=[fact('Assets',43470e6),fact('Liabilities',24776e6),
               fact('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest',18694e6)]
        self.assertEqual(balance(facts,END,ACC)['discrepancy'],0)
    def test_exxon_fixture(self):
        facts=[fact('Assets',369067e6),fact('Liabilities',166594e6),
               fact('StockholdersEquity',195049e6),fact('MinorityInterest',7424e6)]
        r=balance(facts,END,ACC)
        self.assertEqual(r['total_equity'],202473e6)
        self.assertEqual(r['discrepancy'],0)
    def test_unknown_dimensions_rejected(self):
        self.assertFalse(valid({'tag':'Assets','value':1}))
    def test_class_eps_review(self):
        f=fact('EarningsPerShareDiluted',2.5,unit='USD/shares',start='2023-01-01',
               dimensions={'us-gaap:StatementClassOfStockAxis':'ClassAMember'})
        self.assertEqual(diluted_eps([f],END,ACC,start='2023-01-01',primary_class='ClassAMember'),(2.5,'primary_class_review'))
    def test_scale_not_auto_applied(self):
        self.assertTrue(scale_candidate(1e12,1e9)['review_required'])

if __name__=='__main__':unittest.main()
