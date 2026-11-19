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
    self.assertEqual(len(rows),500)
    hydro=[r for r in rows if r.get("isin")=="NO0005052605" and r.get("mic")=="XOSL"]
    self.assertEqual(len(hydro),1)
    self.assertEqual(hydro[0]["id"],"NHY.OL")
    self.assertEqual(len({r["id"] for r in rows}),500)
if __name__=="__main__":unittest.main()
