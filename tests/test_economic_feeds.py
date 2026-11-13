"""Offline tests: validated observations, safe errors, real source matching."""
import json,os,sys,tempfile,unittest,urllib.error
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import economic_feeds as m
class EconomicFeedsTests(unittest.TestCase):
    def test_fred_skips_missing_values(self):
        payload={'observations':[{'date':'2026-11-11','value':'4.1'},{'date':'2026-11-12','value':'.'},{'date':'2026-11-13','value':'4.2'}]}
        with mock.patch.object(m,'request',return_value=payload) as req:
            result=m.fred('DO-NOT-LOG','DGS10')
        self.assertEqual(result['value'],4.2)
        self.assertEqual(len(result['history']),2)
        self.assertNotIn('DO-NOT-LOG',json.dumps(result))
        self.assertIn('api_key=DO-NOT-LOG',req.call_args.args[0])
    def test_eia_facets_and_units(self):
        payload={'response':{'data':[{'series':'RWTC','period':'2026-11-13','value':'72.15'},
           {'series':'RBRTE','period':'2026-11-13','value':'75.42'}]}}
        with mock.patch.object(m,'request',return_value=payload) as req:
            result=m.eia('DO-NOT-LOG','RBRTE')
        self.assertEqual(result['value'],75.42)
        self.assertEqual(result['unit'],'USD/barrel')
        self.assertEqual(len(result['history']),1)
        self.assertIn('facets%5Bseries%5D%5B%5D=RBRTE',req.call_args.args[0])
    def test_eia_has_long_timeout_and_bounded_retries(self):
        payload={'response':{'data':[{'series':'RBRTE','period':'2026-11-12','value':'80.50'}]}}
        with mock.patch.object(m,'request',return_value=payload) as req:
            result=m.eia('TEST-SECRET','RBRTE')
        self.assertEqual(result['value'],80.5)
        self.assertEqual(req.call_args.kwargs,{'timeout':60,'attempts':2})
        self.assertNotIn('TEST-SECRET',json.dumps(result))

    def test_temporary_timeout_is_retried_not_http_401(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def read(self,n):return b'{"response":{"data":[]}}'
        with mock.patch.object(m.urllib.request,'urlopen',side_effect=[TimeoutError('timeout'),Response()]) as op, \
             mock.patch.object(m.time,'sleep') as sleep:
            self.assertEqual(m.request('https://example.org',attempts=2,timeout=60),{'response':{'data':[]}})
            self.assertEqual(op.call_count,2)
            sleep.assert_called_once()
        denied=urllib.error.HTTPError('https://example.org',401,'Unauthorized',None,None)
        with mock.patch.object(m.urllib.request,'urlopen',side_effect=denied) as op:
            with self.assertRaises(urllib.error.HTTPError):
                m.request('https://example.org',attempts=2)
            self.assertEqual(op.call_count,1)

    def test_missing_keys_are_not_failures(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ,{},clear=True):
            result=m.build(Path(tmp))
            self.assertEqual(result['sources']['fred']['status'],'awaiting_key')
            self.assertEqual(result['sources']['eia']['status'],'awaiting_key')
    def test_failed_fetch_preserves_old_values_and_never_leaks_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data').mkdir()
            old={'series':[{'key':'fred:DGS10','value':4.1,'observedAt':'2026-11-10T00:00:00Z'}]}
            (root/'data/economic-feeds.json').write_text(json.dumps(old))
            error=urllib.error.HTTPError('https://api.example.com/?api_key=SENSITIVE',401,'unauthorized',None,None)
            with mock.patch.dict(os.environ,{'STOCKWATCH_FRED_API_KEY':'SENSITIVE'},clear=True),mock.patch.object(m,'fred',side_effect=error):
                result=m.build(root)
            self.assertEqual(result['sources']['fred']['status'],'error')
            self.assertEqual(result['sources']['fred']['errors'][0]['httpStatus'],401)
            self.assertEqual(result['series'][0]['observedAt'],'2026-11-10T00:00:00Z')
            self.assertNotIn('SENSITIVE',json.dumps(result))
if __name__=='__main__':unittest.main()
