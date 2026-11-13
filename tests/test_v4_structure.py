from __future__ import annotations
import json,re,sqlite3,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAGES='index stocks news calendar compare spreads shipping commodities shorts health'.split()
class V4Structure(unittest.TestCase):
 def test_pages_have_shared_navigation_and_correct_scripts(self):
  for name in PAGES:
   html=(ROOT/(name+'.html')).read_text(encoding='utf-8')
   self.assertIn('class="sw-layout"',html,name)
   for target in PAGES:self.assertIn('href="'+target+'.html"',html,name)
   self.assertIn('src="v4.js"',html,name)
 def test_all_routes_have_provenance_and_no_invented_price(self):
  d=json.loads((ROOT/'data/freight-routes.json').read_text())
  self.assertGreaterEqual(len(d['routes']),25)
  self.assertTrue(any(x['vessel']=='Newcastlemax' for x in d['routes']))
  self.assertTrue(any(x['code']=='C5' and x['unit']=='USD/tonne' for x in d['routes']))
  for x in d['routes']:
   self.assertIsNone(x['quote'])
   self.assertTrue(x['sourceUrl'].startswith('https://'))
 def test_news_latest_cap_and_date_headers_in_frontend(self):
  js=(ROOT/'research.js').read_text()
  self.assertIn('archiveNews().slice(0,100)',js)
  self.assertIn('class="news-day"',js)
  self.assertIn("fetchJson('data/news-latest.json')",js)
 def test_open_shipping_activity_separate_from_licensed_rates(self):
  js=(ROOT/'v4.js').read_text(encoding='utf-8')
  health=(ROOT/'research.js').read_text(encoding='utf-8')
  self.assertIn('renderWorldBankPortTraffic()',js)
  self.assertIn("get('data/shipping-ports.json')",js)
  self.assertIn("x.unit==='TEU'",js)
  self.assertIn('not freight prices',js)
  self.assertIn("fetchJson('data/shipping-ports.json')",health)
  self.assertIn('NOT freight prices',health)

 def test_unctad_and_voyage_calculator_are_distinct_from_rates(self):
  js=(ROOT/'v4.js').read_text(encoding='utf-8')
  health=(ROOT/'research.js').read_text(encoding='utf-8')
  self.assertIn('renderUNCTADConnectivity()',js)
  self.assertIn('renderVoyageEstimator()',js)
  self.assertIn('renderPortWatchPermission()',js)
  self.assertIn("get('data/shipping-connectivity.json')",js)
  self.assertIn("fetchJson('data/shipping-connectivity.json')",health)
  self.assertIn('permission_required',health)
  self.assertIn('NOT Baltic assessment',js)

 def test_db_schema_has_source_traceability(self):
  con=sqlite3.connect(':memory:')
  con.executescript((ROOT/'database/0001_core.sql').read_text())
  fields={r[1] for r in con.execute('PRAGMA table_info(news_items)')}
  self.assertTrue({'original_url','source_match','published_at','recorded_at'}.issubset(fields))
  self.assertIn('redistribution_permitted', {r[1] for r in con.execute('PRAGMA table_info(freight_observations)')})
if __name__=='__main__':unittest.main()
