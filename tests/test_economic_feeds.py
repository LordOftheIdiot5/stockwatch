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
