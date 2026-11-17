import json,sys,unittest,tempfile,sqlite3
from pathlib import Path
from datetime import date,timedelta
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from research_assets import report,rights,bars,equity_indicators,pair_indicators,private_build

def series(t="A.X",isin="NO0000000001",mic="XOSL",currency="NOK"):
    return dict(ticker=t,isin=isin,mic=mic,currency=currency,provider="fixture",sourceUrl="https://example.com/data",licenseReference="https://example.com/licence",adjusted=False,bars=[dict(date=str(date(2026,1,1)+timedelta(days=i)),close=100+i,volume=100) for i in range(21)])
def agreement(s):
    return {**{k:s[k] for k in ("provider","sourceUrl","licenseReference","ticker","isin","mic","currency","adjusted")}, "reviewed":True,"evaluationOnly":False,"permanentInternalStorage":True,"derivedResearch":True,"validFrom":"2026-01-01","validThrough":"2027-01-01"}
class ResearchAssetsTests(unittest.TestCase):
    def test_no_trial(self):
        s=series();m=agreement(s);m["evaluationOnly"]=True
        self.assertFalse(rights(m,s,"2026-11-17"))
    def test_mismatch(self):
        s=series();m=agreement(s);m["mic"]="XSTO"
        self.assertFalse(rights(m,s,"2026-11-17"))
    def test_expired(self):self.assertFalse(rights(agreement(series()),series(),"2028-01-01"))
    def test_indicators(self):
        r=equity_indicators(bars(series()));self.assertEqual(len(r),3);self.assertAlmostEqual(r[0][2],0.2)
    def test_no_fill(self):
        s=series();s["bars"][-1]["volume"]=0
        self.assertEqual(equity_indicators(bars(s)),[])
    def test_cross_listing(self):
        a=series();b=series("B.X",mic="XSTO")
        rel=dict(a=a["ticker"],b=b["ticker"],kind="cross_listing",verified=True,sourceUrl="https://example.com/listing")
        self.assertEqual(len(pair_indicators(a,b,rel)),2)
        b["currency"]="SEK";self.assertEqual(pair_indicators(a,b,rel),[])
        b["currency"]="NOK";b["isin"]="NO0000000002";self.assertEqual(pair_indicators(a,b,rel),[])
    def test_fx_requires_exact_date(self):
        a=series();b=series("B.X",mic="XSTO",currency="SEK")
        rel=dict(a=a["ticker"],b=b["ticker"],kind="cross_listing",verified=True,sourceUrl="https://example.com/listing")
        fx=dict(base="NOK",quote="SEK",reviewed=True,rates={v["date"]:1.2 for v in a["bars"]})
        self.assertAlmostEqual(pair_indicators(a,b,rel,fx)[0][2],1.2)
        fx["rates"]={};self.assertEqual(pair_indicators(a,b,rel,fx),[])
    def test_private_build_idempotent_and_gated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"warehouse.sqlite";s=series()
            first=private_build(ROOT,path,[s],{},asof="2026-11-17")
            self.assertEqual(first["licensed_bar"],0)
            second=private_build(ROOT,path,[s],{s["ticker"]:agreement(s)},asof="2026-11-17")
            self.assertEqual(second["licensed_bar"],21)
            self.assertEqual(second,private_build(ROOT,path,[s],{s["ticker"]:agreement(s)},asof="2026-11-17"))
            with sqlite3.connect(path) as db:self.assertEqual(db.execute("SELECT SUM(export_allowed) FROM research_indicator").fetchone()[0],0)
    def test_public_aggregate_only(self):
        r=report(ROOT)["metrics"];self.assertGreaterEqual(r["monitoredListings"],138)
        self.assertNotIn("bars",r)
    def test_repo_db_rejected(self):
        with self.assertRaises(ValueError):private_build(ROOT,ROOT/"bad.sqlite")
if __name__=="__main__":unittest.main()
