"""Source-data and identity regression checks for research tools."""
from __future__ import annotations
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from json import dumps, loads

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_research_data import collect_news, merge_news, extract_events, build_health, build

NOW=datetime(2026,11,12,22,tzinfo=timezone.utc)


def story(headline,ticker='CMBTO.OL',kind='disclosure'):
    return dict(kind=kind,key='source:'+headline,headline=headline,lang='en',published='2026-11-12T07:00:00Z',url='https://newsweb.oslobors.no/message/686290',publisher='Oslo Bors')

class ResearchPipelineTests(unittest.TestCase):
    def setUp(self):
        self.snapshot=dict(generated='2026-11-12T17:06:40Z',companies=[
            dict(ticker='CMBTO.OL',name='CMB.TECH',sector='Shipping',close=165,stories=[story('CMB.TECH announces Q3 2026 results on 26/11/2026')]),
            dict(ticker='MTRS.ST',name='Munters',sector='Industry',close=137,stories=[story('Mutares announces acquisitions',kind='news')]),
            dict(ticker='PERR.PA',name='Gerard Perrier Industrie',sector='Energy',stories=[]),
        ],alerts=[])
        self.watchlist=dict(tickers=[dict(ticker=x['ticker'],name=x['name'],exchange=e) for x,e in zip(self.snapshot['companies'],['Oslo','Stockholm','Paris'])])
    def test_wrong_issuer_excluded_from_news_archive(self):
        items=collect_news(self.snapshot)
        self.assertEqual(len(items),1)
        self.assertEqual(items[0]['ticker'],'CMBTO.OL')
    def test_calendar_never_guesses_a_reporting_date(self):
        self.assertEqual(len(extract_events(collect_news(self.snapshot),NOW)),1)
        self.assertEqual(extract_events(collect_news(self.snapshot),NOW)[0]['date'],'2026-11-26')
        self.assertEqual(extract_events(collect_news(self.snapshot),NOW)[0]['verification'],'provisional')
        self.assertEqual(extract_events([dict(**{**collect_news(self.snapshot)[0], 'headline':'Quarterly results published'})],NOW),[])
    def test_archive_deduplicates_and_retains_prior_runs(self):
        found=collect_news(self.snapshot)
        old={**found[0],'id':'previous','published':'2026-11-10T12:00:00Z'}
        out=merge_news([old],found+found,NOW)
        self.assertEqual(len(out),2)
    def test_news_age_retention(self):
        x=collect_news(self.snapshot)[0]
        old={**x,'published':'2025-01-01T00:00:00Z'}
        self.assertEqual(merge_news([old],[],NOW),[])
    def test_health_keeps_missing_companies(self):
        health=build_health(self.snapshot,self.watchlist,{},NOW)
        self.assertEqual(health['tracked'],3)
        self.assertEqual(health['priced'],2)
        self.assertEqual(health['missing'][0]['ticker'],'PERR.PA')
        self.assertEqual(health['sourceStatus']['Yahoo prices'],'not_instrumented')
    def test_build_end_to_end_without_external_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'data').mkdir()
            (root/'data'/'signals.json').write_text(dumps(self.snapshot))
            (root/'watchlist.json').write_text(dumps(self.watchlist))
            build(root,NOW)
            a=loads((root/'data'/'news-archive.json').read_text())
            e=loads((root/'data'/'events.json').read_text())
            h=loads((root/'data'/'source-health.json').read_text())
            self.assertEqual(len(a['items']),1)
            self.assertEqual(len(e['items']),1)
            self.assertEqual(len(h['missing']),1)
            build(root,NOW+timedelta(hours=1))
            self.assertEqual(len(loads((root/'data'/'news-archive.json').read_text())['items']),1)

if __name__=='__main__':unittest.main()

class SourceTelemetryTests(unittest.TestCase):
    def test_transport_state_distinguishes_errors(self):
        from build_research_data import _provider_status
        v=_provider_status({'providers': {
            'Yahoo prices': {'requests':12,'succeeded':12,'failed':0},
            'MFN filings': {'requests':3,'succeeded':2,'failed':1},
            'Google News': {'requests':2,'succeeded':0,'failed':2},
            'Oslo NewsWeb': {'requests':0,'succeeded':0,'failed':0}
        }})
        self.assertEqual(v['Yahoo prices'],'requests_ok')
        self.assertEqual(v['MFN filings'],'request_errors')
        self.assertEqual(v['Google News'],'requests_failed')
        self.assertEqual(v['Oslo NewsWeb'],'not_observed')
    def test_provider_classification(self):
        from source_telemetry import provider
        self.assertEqual(provider('https://query1.finance.yahoo.com/v8/finance/chart/ASML.AS'),'Yahoo prices')
        self.assertEqual(provider('https://api3.oslo.oslobors.no/v1/newsreader/list'),'Oslo NewsWeb')
        self.assertEqual(provider('https://news.google.com/rss/search?q=ASML'),'Google News')
        self.assertEqual(provider('https://ssr.finanstilsynet.no/api/v2/instruments'),'Finanstilsynet shorts')
