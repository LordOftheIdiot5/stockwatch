import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from marketstack_recovery_probe import validate, probe

DAY="2026-11-16"
BASE={"symbol":"INVE-B.ST","exchange":"XSTO","price_currency":"SEK",
      "date":DAY+"T00:00:00+0000","open":100,"high":110,"low":99,"close":105,"volume":1000}

def check(**changes):
    return validate({"data":[{**BASE,**changes}]},"INVE-B.ST","XSTO","SEK",DAY)

class MarketstackTests(unittest.TestCase):
    def test_exact(self): self.assertEqual(check(),"exact_session_bar")
    def test_old_date(self): self.assertEqual(check(date="2026-11-13T00:00:00+0000"),"session_mismatch")
    def test_wrong_share_class(self): self.assertEqual(check(symbol="INVE-A.ST"),"identity_mismatch")
    def test_wrong_exchange(self): self.assertEqual(check(exchange="XETR"),"identity_mismatch")
    def test_wrong_currency(self): self.assertEqual(check(price_currency="EUR"),"currency_unverified_or_mismatch")
    def test_zero_volume(self): self.assertEqual(check(volume=0),"zero_volume_review")
    def test_bad_ohlc(self): self.assertEqual(check(high=103),"invalid_ohlcv")
    def test_empty(self): self.assertEqual(validate({"data":[]},"INVE-B.ST","XSTO","SEK",DAY),"no_data")
    def test_duplicate(self): self.assertEqual(validate({"data":[BASE,BASE]},"INVE-B.ST","XSTO","SEK",DAY),"ambiguous_response")
    def test_stop_on_provider_error(self):
        called=[]
        def get(symbol,mic,day,key):
            called.append(symbol)
            return {"error":{"code":"invalid_access_key"}}
        rows=probe(["INVE-B.ST","SALM.OL"],DAY,"dummy",get=get,pause=lambda _:None)
        self.assertEqual(called,["INVE-B.ST"])
        self.assertFalse(rows[0]["pricePublicationAllowed"])

if __name__=="__main__":
    unittest.main()
