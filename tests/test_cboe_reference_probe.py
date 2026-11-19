import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from cboe_reference_probe import inspect
class CboeReferenceTests(unittest.TestCase):
    def test_schema_and_exact_id(self):
        raw=b"environment=PROD,created=2026-11-19,time=08:00Z\nisin,mic,currency,live,asset_class,reference_price\nNO0010096985,XOSL,NOK,t,EQTY,123\nNO0010096985,XOSL,NOK,t,EQTY,124\n"
        v=inspect(raw,{("NO0010096985","XOSL")})
        self.assertEqual(v["knownExactISINMICMatches"],1)
        self.assertEqual(v["uniqueLiveEquityIdentities"],1)
        self.assertFalse(v["pricesCollected"])
        self.assertNotIn("reference_price",v)
    def test_cert_rejected(self):
        with self.assertRaises(ValueError):inspect(b"environment=CERT,created=2026-11-19\n",set())
