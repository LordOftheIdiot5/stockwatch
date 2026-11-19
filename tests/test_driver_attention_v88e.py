import sys,unittest
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from driver_attention import build
NOW=datetime(2026,11,19,12,tzinfo=timezone.utc)
WATCH=[{"ticker":"NHY.OL"}]
SEED=[{"id":"XNAS:NVDA","symbol":"NVDA","cik":"0001045810","identityStatus":"sec_ticker_exchange_association"}]
def row(id,date="2026-11-18",**overrides):
    return dict({"id":id,"ticker":"NHY.OL","published":date+"T10:00:00Z","relevance":"strong","type":"disclosure","match":"issuer_code","url":"https://example.com/filing","headline":"New contract","category":"Contracts","driverVersion":1,"driverTags":[{"driver":"potential","basis":"headline category: Contracts"}]},**overrides)
class Attention(unittest.TestCase):
    def test_windows_and_evidence(self):
        d=build([row("a"),row("b","2026-11-09",relevance="mentioned"),row("c","2026-11-19"),row("d",duplicateOf="a"),row("e",relevance="review"),row("f","2026-11-20"),row("a")],WATCH,SEED,NOW)
        r=d["listings"]["NHY.OL"]
        self.assertEqual(r["recent7"],{"issuer":1,"media":0})
        self.assertEqual(r["prior7"],{"issuer":0,"media":1})
        self.assertEqual(r["observedRecords"],3)
        self.assertEqual(len(r["daily"]),14)
        self.assertEqual(len(r["potential"]),3)
        self.assertEqual(r["topicCounts"]["potential"],1)
    def test_exact_sec_identity_and_unconnected_reference(self):
        good=row("sec",ticker="NVDA",sourceIssuer="0001045810",sourceFeed="sec_edgar")
        d=build([good,{**good,"id":"bad","sourceIssuer":"0000000000"},row("reference",ticker="MOWI")],WATCH,SEED,NOW)
        self.assertEqual(d["listings"]["XNAS:NVDA"]["observedRecords"],1)
        self.assertNotIn("MOWI",d["listings"])
    def test_warning_is_not_growth(self):
        r=build([row("w",headline="Company issues profit warning",category="Guidance")],WATCH,SEED,NOW)["listings"]["NHY.OL"]
        self.assertEqual(r["potential"][0]["topic"],"Guidance / warning")
