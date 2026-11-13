from __future__ import annotations
import json,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from news_quality import association,annotate,summary,topic,norm
from build_spread_observations import build as build_obs
from build_research_data import build as build_all

class FinalResearch(unittest.TestCase):
 def test_unrelated_competitor_is_not_automatically_issuer_news(self):
  item={'ticker':'NOVO-B.CO','name':'Novo Nordisk','headline':'Eli Lilly wins approval of drug','match':'name_mentioned'}
  self.assertEqual(association(item),'review')
 def test_ambiguous_similar_issuer_flagged(self):
  item={'ticker':'SIE.DE','name':'Siemens','headline':'Siemens Energy signs a contract','match':'name_mentioned'}
  self.assertEqual(association(item),'review')
 def test_real_issuer_and_filing_confidence(self):
  x={'ticker':'SIE.DE','name':'Siemens','headline':'Siemens reports results','match':'name_mentioned'}
  self.assertEqual(association(x),'mentioned')
  self.assertEqual(association(dict(x,match='issuer_code',type='disclosure')),'strong')
 def test_near_names_do_not_match_substrings(self):
  self.assertEqual(association({'ticker':'ABC.OL','name':'Tryg','headline':'Trigger prices rise'}),'review')
  self.assertEqual(norm('Gérard Perrier Industrie'),'gerard perrier industrie')
 def test_topic_classification(self):
  self.assertEqual(topic('Company announces dividend'),'Dividends')
  self.assertEqual(topic('Company reports quarterly results'),'Earnings / results')
 def test_dedup_keeps_archive_records(self):
  records=[]
  for date,name in [('2026-11-13T08:00:00Z','A'),('2026-11-13T07:00:00Z','B')]:
   records.append({'id':name,'ticker':'VWS.CO','name':'Vestas','type':'news','headline':'Vestas wins major contract in Norway','match':'name_mentioned','published':date,'url':'https://source.example/'+name})
  out=annotate(records)
  self.assertEqual(len(out),2)
  self.assertEqual(summary(out)['duplicates'],1)
  self.assertEqual(summary(out)['relevant'],1)
 def test_snapshots_append_daily_no_history_fabrication(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'data').mkdir()
   now=datetime(2026,11,13,12,tzinfo=timezone.utc)
   context={'generated':now.isoformat(),'shareClasses':[{'a':'A.ST','b':'B.ST','ratio':1.02}]}
   (root/'data/context.json').write_text(json.dumps(context))
   d=build_obs(root,now)
   self.assertEqual(len(d['pairs']['A.ST/B.ST']),1)
   context['shareClasses'][0]['ratio']=1.05
   (root/'data/context.json').write_text(json.dumps(context))
   d=build_obs(root,now)
   self.assertEqual(d['pairs']['A.ST/B.ST'],[{'date':'2026-11-13','value':1.05}])
   context['generated']=datetime(2026,11,14,12,tzinfo=timezone.utc).isoformat()
   (root/'data/context.json').write_text(json.dumps(context))
   d=build_obs(root,now+timedelta(days=1))
   self.assertEqual(len(d['pairs']['A.ST/B.ST']),2)
 def test_automated_datasets_and_quality_report(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);folder=root/'data';folder.mkdir()
   now=datetime(2026,11,13,12,tzinfo=timezone.utc)
   watch={'tickers':[{'ticker':'ALPER.PA','name':'Gerard Perrier Industrie','exchange':'Paris','sector':'Grid & energy'}]}
   signal={'generated':now.isoformat(),'companies':[{'ticker':'ALPER.PA','name':'Gerard Perrier Industrie','sector':'Grid & energy','close':75,'stories':[{'kind':'news','headline':'Gerard Perrier Industrie announces contract','url':'https://example.org/story','published':now.isoformat(),'publisher':'Issuer'}]}]}
   context={'generated':now.isoformat(),'shareClasses':[{'a':'X.ST','b':'Y.ST','ratio':1.1}]}
   (root/'watchlist.json').write_text(json.dumps(watch));(folder/'signals.json').write_text(json.dumps(signal));(folder/'context.json').write_text(json.dumps(context));(folder/'freight-routes.json').write_text(json.dumps({'routes':[{'code':'C3','unit':'USD/tonne'}]}))
   build_all(root,now)
   for file in ['news-quality.json','issuer-identities.json','spread-observations.json','dataset-catalog.json']:
    self.assertTrue((folder/file).exists(),file)
   h=json.loads((folder/'source-health.json').read_text())
   self.assertEqual(h['priced'],1)
   self.assertEqual(h['newsQuality']['relevant'],1)
   self.assertEqual(h['abRatios']['snapshotPairs'],1)
   ident=json.loads((folder/'issuer-identities.json').read_text())
   self.assertEqual(ident['entities'][0]['isin'],'FR0000061459')

if __name__=='__main__':unittest.main()
