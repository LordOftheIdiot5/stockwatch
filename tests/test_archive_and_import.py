from __future__ import annotations
import csv,json,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from build_monthly_archive import build as build_monthly
from import_licensed_history import import_csv

class MarketHistoryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  (self.root/'data').mkdir();(self.root/'watchlist.json').write_text(json.dumps({'tickers':[{'ticker':'TEST.OL'}]}))
  (self.root/'data/freight-routes.json').write_text(json.dumps({'routes':[{'code':'C3','unit':'USD/t'}]}))
  self.rows=self.root/'bars.csv';self.manifest=self.root/'manifest.json'
 def write_rows(self,headers,rows):
  with self.rows.open('w',newline='') as f:
   w=csv.DictWriter(f,headers);w.writeheader();w.writerows(rows)
 def manifest_data(self,typ,**kw):
  v={'assetType':typ,'redistributionPermitted':True,'provider':'Licensed Sample Provider','licenseReference':'https://licenses.example.com/stockwatch','sourceUrl':'https://source.example.com/series',**kw};self.manifest.write_text(json.dumps(v))
 def test_refuses_unauthorized_history(self):
  self.write_rows(['date','close','volume'],[{'date':'2026-11-01','close':'10','volume':'100'},{'date':'2026-11-02','close':'12','volume':'100'},{'date':'2026-11-03','close':'11','volume':'100'}]);self.manifest_data('equity',ticker='TEST.OL',currency='NOK',adjusted=False,redistributionPermitted=False)
  with self.assertRaisesRegex(ValueError,'redistribution'):import_csv(self.root,self.rows,self.manifest)
  self.assertFalse((self.root/'data/history').exists())
 def test_import_equity_history_with_license(self):
  self.write_rows(['date','close','volume'],[{'date':'2026-11-03','close':'11','volume':'100'},{'date':'2026-11-01','close':'10','volume':'100'},{'date':'2026-11-02','close':'12','volume':'100'}]);self.manifest_data('equity',ticker='TEST.OL',currency='NOK',adjusted=False)
  out=import_csv(self.root,self.rows,self.manifest);data=json.loads(out.read_text());self.assertEqual(len(data['bars']),3);self.assertTrue(data['redistributionPermitted']);self.assertEqual(data['bars'][0]['date'],'2026-11-01')
 def test_reject_wrong_freight_unit(self):
  self.write_rows(['date','value'],[{'date':'2026-11-01','value':'100'},{'date':'2026-11-02','value':'110'},{'date':'2026-11-03','value':'105'}]);self.manifest_data('freight',routeCode='C3',unit='USD/day')
  with self.assertRaisesRegex(ValueError,'unit'):import_csv(self.root,self.rows,self.manifest)

class DurableArchiveTests(unittest.TestCase):
 def test_two_months_persist_and_deduplicate(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);data=root/'data';data.mkdir()
   def snapshot(day,key):
    return {'generated':day,'companies':[{'ticker':'TEST.OL','name':'Test Company','sector':'Tech','stories':[{'kind':'news','key':key,'headline':'Test Company reports results','url':f'https://sources.example.com/{key}','published':day,'publisher':'Issuer'}]}],'alerts':[]}
   (data/'signals.json').write_text(json.dumps(snapshot('2026-10-15T12:00:00Z','first')))
   one=build_monthly(root,datetime(2026,10,20,tzinfo=timezone.utc));self.assertEqual(one['total'],1)
   (data/'signals.json').write_text(json.dumps(snapshot('2026-11-01T12:00:00Z','second')))
   two=build_monthly(root,datetime(2026,11,5,tzinfo=timezone.utc));self.assertEqual(two['total'],2)
   three=build_monthly(root,datetime(2026,11,5,tzinfo=timezone.utc));self.assertEqual(three['total'],2)
   self.assertEqual([m['month'] for m in three['months']],['2026-11','2026-10'])
if __name__=='__main__':unittest.main()
