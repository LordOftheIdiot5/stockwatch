import json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class CompanyResearchTests(unittest.TestCase):
    def test_onboarding_is_separate_from_scanner(self):
        d=json.loads((ROOT/'data/research-onboarding.json').read_text())
        watch=json.loads((ROOT/'watchlist.json').read_text())['tickers']
        current={r['ticker'].removesuffix('.OL') for r in watch}
        rows=d['records']
        self.assertEqual(len(rows),17)
        self.assertEqual(len({x['isin'] for x in rows}),len(rows))
        for x in rows:
            self.assertNotIn(x['ticker'],current)
            self.assertEqual(x['mic'],'XOSL')
            self.assertEqual(x['quoteStatus'],'not_connected')
            self.assertRegex(x['isin'],r'^[A-Z]{2}[A-Z0-9]{9}\d$')
            self.assertTrue(x['sourceUrl'].startswith('https://live.euronext.com/'))
            self.assertNotIn('close',x)
    def test_company_research_page_contract(self):
        js=(ROOT/'v4.js').read_text()
        html=(ROOT/'company.html').read_text()
        self.assertIn('data-page="company"',html)
        self.assertIn('companyPage()',js)
        self.assertIn('No tracked listing matches this identifier',js)
        self.assertIn('not a verified ownership',js)
        self.assertIn('container.dataset.currentTicker!==t',js)
        self.assertIn('No simulated history',js)
if __name__=='__main__':unittest.main()
