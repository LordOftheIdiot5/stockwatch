import tempfile,json,sys,unittest
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from licensed_scanner import select_chart
class LicensedScannerTests(unittest.TestCase):
 def test_prefer_authorized_and_keep_provenance(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"data/history";p.mkdir(parents=True)
   t={"ticker":"X.OL","exchange":"Oslo"}
   now=datetime(2026,11,17,tzinfo=timezone.utc)
   doc={"ticker":"X.OL","currency":"NOK","redistributionPermitted":True,"adjusted":False,"source":"Example licensed provider","sourceUrl":"https://example.org/data","licenseReference":"https://example.org/grant","bars":[{"date":"2026-11-13","close":10,"volume":200},{"date":"2026-11-16","close":11,"volume":100}]}
   def forbidden(ticker):self.fail("legacy provider must not be called")
   (p/"X.OL.json").write_text(json.dumps(doc))
   chart,status=select_chart(Path(d),t,now,forbidden,2)
   self.assertEqual(status,"licensed_history");self.assertEqual(chart["bars"][-1]["close"],11);self.assertTrue(chart["priceProvenance"]["redistributionPermitted"])
   for patch in ({"currency":"SEK"},{"adjusted":True},{"redistributionPermitted":False},{"bars":[doc["bars"][0],doc["bars"][0]]}):
    (p/"X.OL.json").write_text(json.dumps({**doc,**patch}))
    self.assertEqual(select_chart(Path(d),t,now,forbidden,2),(None,"licensed_history_invalid"))
   (p/"X.OL.json").unlink()
   self.assertEqual(select_chart(Path(d),t,now,forbidden,2,True),(None,"licensed_history_missing"))
   result,status=select_chart(Path(d),t,now,lambda t:{"bars":[]},2)
   self.assertEqual(status,"legacy_chart");self.assertEqual(result["priceProvenance"]["publicationRights"],"not_verified")
