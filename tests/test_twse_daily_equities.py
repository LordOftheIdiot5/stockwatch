import sys,unittest,io
from pathlib import Path
from datetime import date
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from twse_daily_equities import parse,archive
DAY=date(2026,11,19)
ROW={"Date":"1151119","Code":"2330","Name":"Test","TradeVolume":"1,000","TradeValue":"100,000","OpeningPrice":"100","HighestPrice":"105","LowestPrice":"99","ClosingPrice":"104","Change":"+4","Transaction":"10"}
class Client:
    def __init__(self):self.objects={}
    def put(self,c,b,k,m,t):
        state="already_present" if k in self.objects else "created";self.objects[k]=b;return state
    def get_object(self,**kw):return {"Body":io.BytesIO(self.objects[kw["Key"]])}
class Tests(unittest.TestCase):
    def test_date_and_prices(self):
        d=parse([ROW],DAY);self.assertEqual(d["sessionDate"],str(DAY));self.assertEqual(d["records"][0]["securityId"],"XTAI:2330");self.assertEqual(d["records"][0]["close"],"104")
    def test_no_volume_not_fabricated(self):
        r={**ROW,"Code":"1234","TradeVolume":"0","OpeningPrice":"--","HighestPrice":"--","LowestPrice":"--","ClosingPrice":"--"}
        d=parse([ROW,r],DAY);self.assertIsNone(d["records"][0]["close"]);self.assertEqual(d["records"][0]["status"],"no_volume")
    def test_mixed_day_and_duplicates(self):
        for rs in ([ROW,ROW],[ROW,{**ROW,"Code":"1234","Date":"1151118"}]):
            with self.assertRaises(ValueError):parse(rs,DAY)
    def test_invalid_ohlc_and_future(self):
        for r in ({**ROW,"HighestPrice":"90"},{**ROW,"Date":"1151120"}):
            with self.assertRaises(ValueError):parse([r],DAY)
    def test_idempotent_verified_archive(self):
        c=Client();d=parse([ROW],DAY)
        with patch("private_r2_archive.immutable_put",c.put):
            a=archive(c,d,b"source");b=archive(c,d,b"source")
        self.assertTrue(a["readbackVerified"]);self.assertEqual(b["storageStatus"],"already_present");self.assertEqual(len(c.objects),2)

    def test_quarantine_numeric_exception_without_inventing_price(self):
        bad={**ROW,"Code":"9999","ClosingPrice":"unknown"}
        d=parse([ROW,bad],DAY)
        self.assertEqual(d["quarantined"],1)
        x=d["records"][1]
        self.assertEqual(x["status"],"quarantined")
        self.assertIsNone(x["close"])
        self.assertIsNone(x["volume"])
    def test_quarantine_threshold(self):
        with self.assertRaises(ValueError):
            parse([ROW,{**ROW,"Code":"9998","ClosingPrice":"unknown"},{**ROW,"Code":"9999","ClosingPrice":"unknown"}],DAY)
