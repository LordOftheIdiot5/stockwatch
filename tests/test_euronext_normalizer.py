import io,zipfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import euronext_normalizer as n
FIELDS=["TradingDateTime","PublicationDateTime","MifidInstrumentID","MifidPrice","MifidQuantity","MifidCurrency","Venue","TradeUniqueIdentifier","FixtureFlag"]
def archive(records):
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:z.writestr("trades.csv","fixture\n"+",".join(FIELDS)+"\n"+"\n".join(",".join(x) for x in records))
    return b.getvalue()
def row(id,price,flag="TEST_ORDINARY",minute="01"):
    return [f"2025-01-03T09:{minute}:00Z","2025-01-03T18:00:00Z","NO0010096985",price,"2","NOK","XOSL",id,flag]
class NormalizerTests(unittest.TestCase):
 def setUp(self):
    self.p={"reviewed":True,"specificationReference":"synthetic fixture only","flagColumns":["FixtureFlag"],"expectedColumns":FIELDS,"eligibleFlagTuples":[["TEST_ORDINARY"]],"excludedFlagTuples":[["TEST_EXCLUDED"]]}
    self.m={("XOSL","NO0010096985"):{"listingId":"ref:XOSL:EQNR","currency":"NOK"}}
 def test_snapshot(self):
    a=row("a","10")
    r=n.snapshot(archive([a,a,row("b","12",minute="02"),row("c","99","TEST_EXCLUDED")]),self.p,self.m)
    self.assertEqual(r["bars"][0]["close"],"12");self.assertEqual(r["bars"][0]["volume"],"4")
    self.assertFalse(r["bars"][0]["publicPublicationAllowed"])
 def test_quarantine(self):
    for bad in [row("a","11"),row("b","12","UNKNOWN_CORRECTION")]:
        r=n.snapshot(archive([row("a","10"),bad]),self.p,self.m)
        self.assertEqual(r["bars"],[]);self.assertEqual(len(r["quarantinedSessions"]),1)
 def test_review_required(self):
    with self.assertRaises(ValueError):n.snapshot(archive([]),{**self.p,"reviewed":False},self.m)

 def test_real_report_price_notation_and_correction_guard(self):
    fields=FIELDS+["MifidPriceNotation","MissingPrice","MmtModificationIndicator","MmtContributionToPrice"]
    def raw(mod="-",notation="MONE",missing="",contribution="P"):
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w") as z:
            z.writestr("trades.csv",",".join(fields)+"\n"+",".join(row("a","10")+[notation,missing,mod,contribution]))
        return b.getvalue()
    flags=["FixtureFlag","MmtModificationIndicator","MmtContributionToPrice"]
    p={**self.p,"expectedColumns":fields,"flagColumns":flags,"reviewedNoMissingPriceCodes":[""],"eligibleFlagTuples":[["TEST_ORDINARY","-","P"]],"excludedFlagTuples":[]}
    self.assertEqual(len(n.snapshot(raw(),p,self.m)["bars"]),1)
    for kwargs in [{"notation":"PERC"},{"missing":"MISSING"},{"mod":"CANC"},{"mod":"AMND"},{"contribution":"NPFT"},{"contribution":"TNCP"}]:
        policy={**p,"eligibleFlagTuples":[["TEST_ORDINARY",kwargs.get("mod","-"),kwargs.get("contribution","P")]]}
        out=n.snapshot(raw(**kwargs),policy,self.m)
        self.assertEqual(out["bars"],[])
        self.assertEqual(len(out["quarantinedSessions"]),1)
    with self.assertRaises(ValueError):n.snapshot(raw(),{**p,"reviewedNoMissingPriceCodes":[]},self.m)
    with self.assertRaises(ValueError):n.snapshot(raw(),{**p,"flagColumns":["FixtureFlag"],"eligibleFlagTuples":[["TEST_ORDINARY"]]},self.m)
if __name__=="__main__":unittest.main()
