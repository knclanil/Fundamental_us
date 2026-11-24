import unittest
from datetime import date
from fundamentals.normalize import normalize


def fact(start, end, fy, fp, form, val, filed='2026-11-01'):
    row={'end':end,'fy':fy,'fp':fp,'form':form,'val':val,'filed':filed,'accn':'fixture'}
    if start is not None: row['start']=start
    return row

class FiscalCalendarTests(unittest.TestCase):
    def test_aos_year_end_comparative_not_fy2022q1(self):
        facts={'Revenues':{'units':{'USD':[
            fact('2021-01-01','2021-12-31',2022,'FY','10-K',1000, '2022-02-01'),
            fact('2022-07-01','2022-09-30',2022,'Q3','10-Q',300)]}},
            'Assets':{'units':{'USD':[
            fact(None,'2021-12-31',2022,'Q3','10-Q',3474400000),
            fact(None,'2021-12-31',2021,'FY','10-K',3474400000,'2022-02-01')]}}}
        rows=normalize({'facts':{'us-gaap':facts}},today=date(2026,11,24))
        self.assertFalse(any(r['period']=='FY2022Q1' for r in rows))
        self.assertFalse(any(r['period_type']=='quarterly' and r['period_end']=='2021-12-31' for r in rows))
        self.assertTrue(any(r['period']=='FY2021' for r in rows))
        self.assertTrue(any(r['period']=='FY2022Q3' for r in rows))

    def test_acn_august_fiscal_year(self):
        facts={'Revenues':{'units':{'USD':[
            fact('2025-09-01','2026-08-31',2026,'FY','10-K',740),
            fact('2025-12-01','2026-02-28',2026,'Q2','10-Q',200)]}}}
        rows=normalize({'facts':{'us-gaap':facts}},today=date(2026,11,24))
        self.assertEqual({r['period'] for r in rows},{'FY2026','FY2026Q2'})

    def test_2025_comparative_2026_filing_mapped_to_2025(self):
        facts={'Revenues':{'units':{'USD':[
            fact('2025-01-01','2025-12-31',2026,'FY','10-K',900),
            fact('2025-07-01','2025-09-30',2026,'Q3','10-Q',250),
            fact('2026-07-01','2026-09-30',2026,'Q3','10-Q',350)]}}}
        rows=normalize({'facts':{'us-gaap':facts}},today=date(2026,11,24))
        self.assertTrue(any(r['period']=='FY2025Q3' for r in rows))
        self.assertTrue(any(r['period']=='FY2026Q3' for r in rows))

if __name__=='__main__':unittest.main()
