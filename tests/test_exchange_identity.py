import io,zipfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import exchange_identity as m
class ExchangeIdentityTests(unittest.TestCase):
 def test_isin(self):
    self.assertTrue(m.valid_isin("NO0010096985"))
    self.assertTrue(m.valid_isin("US0378331005"))
    self.assertFalse(m.valid_isin("NO0010096986"))
 def test_archive_exact_venue(self):
    b=io.BytesIO()
    fields=["TradingDateTime","PublicationDateTime","MifidInstrumentID","MifidPrice","MifidQuantity","MifidCurrency","Venue","TradeUniqueIdentifier"]
    with zipfile.ZipFile(b,"w") as z:
        z.writestr("trades.csv","copyright\n"+";".join(fields)+"\n"+";;NO0010096985;10;1;NOK;XOSL;x\n;;NO0010096985;11;1;NOK;XOSL;y\n;;US0378331005;10;1;USD;XNAS;z\n")
    self.assertEqual(m.trade_keys(b.getvalue(),"XOSL"),[("NO0010096985","XOSL")])
 def test_unique_exact_match_and_conflict(self):
    rows=[{"id":"ref:XOSL:EQNR","mic":"XOSL","figi":"BBG000NSV6T3","isin":"NO0010096985"}]
    def fetch(j,k):
        self.assertEqual(j[0]["micCode"],"XOSL")
        return [{"data":[{"figi":"BBG000NSV6T3","marketSector":"Equity"}]}]
    good,c=m.reconcile([("NO0010096985","XOSL")],rows,"fixture",fetch)
    self.assertEqual(len(good),1);self.assertFalse(good[0]["pricePublicationAllowed"])
    bad,c=m.reconcile([("US0378331005","XOSL")],rows,"fixture",fetch)
    self.assertEqual(bad,[]);self.assertEqual(c["conflicting_identity"],1)
    bad,c=m.reconcile([("NO0010096985","XOSL")],rows+[dict(rows[0],id="duplicate")],"fixture",fetch)
    self.assertEqual(bad,[]);self.assertEqual(c["ambiguous_listing"],1)
 def test_ambiguous_figi(self):
    def fetch(j,k):
        return [{"data":[{"figi":"BBG000NSV6T3","marketSector":"Equity"},{"figi":"BBG000NSV6T4","marketSector":"Equity"}]}]
    a,c=m.reconcile([("NO0010096985","XOSL")],[],"fixture",fetch)
    self.assertEqual(a,[]);self.assertEqual(c["ambiguous_figi"],1)
 def test_universe(self):
    rows=m.universe()
    self.assertGreaterEqual(len(rows),507)
    self.assertEqual(len({r["id"] for r in rows}),len(rows))
    required={"BBG000BKSXB7","BBG000BDD8Z8","BBG000BP71K9","BBG000BP73C4","BBG000BDZQP5","BBG000BCCG29","BBG000BFQ1Y5"}
    self.assertTrue(required.issubset({r.get("figi") for r in rows}))
if __name__=="__main__":unittest.main()
