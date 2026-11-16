import json,tempfile,unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import import_reference_prices as p
class ReferencePriceTests(unittest.TestCase):
    def test_explicit_rights_and_append_only(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);data=root/"data";data.mkdir()
            p.write(data/"research-targets.json",{"targets":[{"id":"XOSL:EQNR","mic":"XOSL"}]})
            p.write(data/"research-expansion.json",{"records":[]})
            id="ref:XOSL:EQNR"
            grant={"provider":"Fixture only","sourceUrl":"https://example.invalid/feed","licenseReference":"https://example.invalid/license","publicRawRedistribution":False,"publicDisplay":True,"historicalStorage":True,"derivedAnalytics":True,"identityReviewed":True,"priceType":"end_of_day","listings":{id:{"mic":"XOSL","providerSymbol":"TEST","currency":"NOK","adjusted":False}}}
            mf=root/"grant.json";csv=root/"feed.csv"
            p.write(mf,grant)
            csv.write_text("listing_id,date,close,volume\n"+id+",2025-01-02,100,200\n"+id+",2025-01-03,102,300\n")
            with self.assertRaisesRegex(ValueError,"publicRawRedistribution"):p.import_batch(root,csv,mf)
            self.assertFalse((root/p.OUT).exists())
            grant["publicRawRedistribution"]=True;p.write(mf,grant)
            d=p.import_batch(root,csv,mf);r=d["records"][0]
            self.assertEqual(r["changePct"],2);self.assertEqual(r["observations"],2)
            dest=root/r["historyPath"];before=dest.read_bytes()
            csv.write_text("listing_id,date,close,volume\n"+id+",2025-01-03,999,300\n")
            with self.assertRaisesRegex(ValueError,"Conflicting"):p.import_batch(root,csv,mf)
            self.assertEqual(dest.read_bytes(),before)
            csv.write_text("listing_id,date,close,volume\n"+id+",2025-01-06,101,500\n")
            r=p.import_batch(root,csv,mf)["records"][0]
            self.assertEqual(r["observations"],3);self.assertEqual(r["previousDate"],"2025-01-03")
            self.assertEqual(r["firstDate"],"2025-01-02")
if __name__=="__main__":unittest.main()
