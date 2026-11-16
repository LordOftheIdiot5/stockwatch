import sqlite3,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import private_trade_bars as m
class PrivateBarsTests(unittest.TestCase):
 def setUp(self):
    self.db=sqlite3.connect(":memory:")
    self.mapping={("XOSL","NO0010096985"):"ref:XOSL:EQNR"}
 def event(self,id,price,minute=0,revision=0,action="upsert",eligible=True):
    return dict(mic="XOSL",isin="NO0010096985",listingId="ref:XOSL:EQNR",sessionDate="2025-01-03",tradeId=id,revision=revision,action=action,currency="NOK",eligible=eligible,tradeTime=f"2025-01-03T09:{minute:02d}:00Z",eventTime="2025-01-03T18:00:00Z",price=price,quantity="2")
 def test_replay_correction_cancel(self):
    a,b,c=self.event("a","10"),self.event("b","14",1),self.event("c","12",2)
    m.ingest(self.db,[a,b,c,a],self.mapping)
    x=m.bars(self.db)[0]
    self.assertEqual((x["open"],x["high"],x["close"],x["volume"]),("10","14","12","6"))
    m.ingest(self.db,[self.event("b","11",1,1),self.event("c","12",2,1,"cancel")],self.mapping)
    x=m.bars(self.db)[0]
    self.assertEqual((x["high"],x["close"],x["volume"]),("11","11","4"))
    self.assertFalse(x["officialClose"]);self.assertFalse(x["publicPublicationAllowed"])
    with self.assertRaises(ValueError):m.ingest(self.db,[self.event("a","99")],self.mapping)
    self.assertEqual(m.bars(self.db)[0]["open"],"10")
 def test_same_time_and_eligibility(self):
    m.ingest(self.db,[self.event("a","10"),self.event("b","12"),self.event("c","999",1,eligible=False)],self.mapping)
    x=m.bars(self.db)[0];self.assertIsNone(x["open"]);self.assertIsNone(x["close"]);self.assertEqual(x["high"],"12")
 def test_reject_unreviewed(self):
    with self.assertRaises(ValueError):m.ingest(self.db,[self.event("a","10")],{})
    with self.assertRaises(ValueError):m.private_path(m.ROOT/"data/trades.sqlite")
if __name__=="__main__":unittest.main()
