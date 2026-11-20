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
            d=p.import_batch(root,csv,mf);r=d["records"][0]
            self.assertTrue(r["publicDisplayPermitted"])
            self.assertFalse(r["rawRedistributionPermitted"])
            self.assertFalse(r["redistributionPermitted"])
            self.assertTrue(p.read(root/r["historyPath"])["publicDisplayPermitted"])
            self.assertEqual(r["changePct"],2);self.assertEqual(r["observations"],2)
            dest=root/r["historyPath"];before=dest.read_bytes()
            csv.write_text("listing_id,date,close,volume\n"+id+",2025-01-03,999,300\n")
            with self.assertRaisesRegex(ValueError,"Conflicting"):p.import_batch(root,csv,mf)
            self.assertEqual(dest.read_bytes(),before)
            csv.write_text("listing_id,date,close,volume\n"+id+",2025-01-06,101,500\n")
            r=p.import_batch(root,csv,mf)["records"][0]
            self.assertEqual(r["observations"],3);self.assertEqual(r["previousDate"],"2025-01-03")
            self.assertEqual(r["firstDate"],"2025-01-02")
    def test_public_display_cannot_be_inferred_from_raw_rights(self):
        grant={"provider":"Test","sourceUrl":"https://example.invalid/feed","licenseReference":"https://example.invalid/rights","publicRawRedistribution":True,"publicDisplay":False,"historicalStorage":True,"derivedAnalytics":True,"identityReviewed":True,"priceType":"end_of_day","listings":{"ref:XOSL:EQNR":{"mic":"XOSL","providerSymbol":"TEST","currency":"NOK","adjusted":False}}}
        with self.assertRaisesRegex(ValueError,"publicDisplay"):p.validate_grant(grant)
        grant["publicDisplay"]=True
        grant["historicalStorage"]=False
        with self.assertRaisesRegex(ValueError,"historicalStorage"):p.validate_grant(grant)
        grant["historicalStorage"]=True
        del grant["publicRawRedistribution"]
        with self.assertRaisesRegex(ValueError,"publicRawRedistribution"):p.validate_grant(grant)
if __name__=="__main__":unittest.main()
