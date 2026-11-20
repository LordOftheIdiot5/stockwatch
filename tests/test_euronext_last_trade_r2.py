import io,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import euronext_last_trade_r2 as r
Q={"listingId":"ref:XOSL:EQNR","mic":"XOSL","date":"2026-11-19","currency":"NOK",
   "lastTradePrice":"123.45","lastTradeAt":"2026-11-19T15:30:00+00:00",
   "observedEligibleTrades":100,"classification":r.CLASSIFICATION,
   "officialClose":False,"publicPublicationAllowed":False,"historicalRetentionApproved":False}
M=[{"market":"OSL","sourceSha256":"a"*64,"eligibleListings":45}]
class Store:
    def __init__(self):self.rows={}
    def put(self,client,body,key,metadata,content_type):
        present=key in self.rows
        if not present:self.rows[key]=body
        return "already_present" if present else "created"
    def get_object(self,**kwargs):return {"Body":io.BytesIO(self.rows[kwargs["Key"]])}
class Tests(unittest.TestCase):
    def test_dated_private_archive_and_retry_idempotency(self):
        c=Store()
        with patch("euronext_last_trade_r2.immutable_put",c.put):
            a=r.archive(c,[Q],M,"2026-11-20T12:00:00+00:00")
            b=r.archive(c,[Q],M,"2026-11-20T12:01:00+00:00")
        self.assertTrue(a["readbackVerified"])
        self.assertEqual(a["retainedObservations"],1)
        self.assertEqual(b["markets"][0]["storageStatus"],"already_present")
        self.assertEqual(len(c.rows),3) # one immutable content, two receipts
        self.assertNotIn("123.45",str(a))
        self.assertFalse(a["publicPublication"])
    def test_rejects_false_rights_claims(self):
        for bad in ({**Q,"publicPublicationAllowed":True},{**Q,"officialClose":True},
                    {**Q,"historicalRetentionApproved":True},
                    {**Q,"classification":"official_daily_close"}):
            with self.assertRaisesRegex(ValueError,"rights claim"):
                r.checked([bad],M)
    def test_refuses_conflicting_venue_and_session(self):
        for bad in ({**Q,"mic":"XPAR"},{**Q,"date":"2026-11-18"},{**Q,"currency":"EUR","lastTradePrice":"NaN"}):
            with self.assertRaises(ValueError):r.checked([bad],M)
    def test_rejects_duplicate_identifiers(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):r.checked([Q,Q],M)
    def test_rejects_bogus_source(self):
        with self.assertRaisesRegex(ValueError,"provenance"):r.checked([Q],[{**M[0],"sourceSha256":"BAD"}])
    def test_requires_explicit_internal_retention(self):
        with patch.dict("os.environ",{"STOCKWATCH_EURONEXT_STAGE_RETENTION_APPROVED":"false"}):
            with self.assertRaisesRegex(ValueError,"retention scope"):r.archive_live([Q],M)
    def test_readback_mismatch_blocks(self):
        c=Store()
        c.get_object=lambda **kw:{"Body":io.BytesIO(b"tampered")}
        with patch("euronext_last_trade_r2.immutable_put",c.put):
            with self.assertRaisesRegex(ValueError,"readback mismatch"):r.archive(c,[Q],M,"2026-11-20T12:00:00+00:00")
if __name__=="__main__":unittest.main()
