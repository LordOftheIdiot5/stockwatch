import io,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from listing_identity_r2 import prepare,archive
R={"listingId":"A","isin":"NO0010096985","mic":"XOSL","figi":"BBG000BXRMY9","lei":"5493001KJTIIGC8Y1R12","cfi":"ESVUFR","currency":"NOK","status":"exact_candidate_join","reviewRequired":True,"pricePublicationAllowed":False}
S={"group":"euronext","sourceDate":"2026-11-14","sourceParts":[{"name":"FULINS_E_20261114_01of01.zip","sha256":"a"*64,"rows":1}],"sourceRows":1,"candidateMatches":1,"currentStateEstablished":False,"publishedPrices":0}
T={"A":(R["figi"],R["mic"])}
class Client:
    def __init__(self):self.data={}
    def put(self,client,body,key,metadata,content_type):
        state="already_present" if key in self.data else "created";self.data[key]=body;return state
    def get_object(self,**kw):return {"Body":io.BytesIO(self.data[kw["Key"]])}
class Tests(unittest.TestCase):
    def test_valid_candidate(self):
        a=prepare(S,[R],T);self.assertEqual(a["candidateMatches"],1);self.assertFalse(a["publicPublication"])
    def test_bad_claim_and_conflict(self):
        for s,r,t in [({**S,"currentStateEstablished":True},R,T),(S,{**R,"pricePublicationAllowed":True},T),(S,R,{"A":("wrong","XOSL")})]:
            with self.assertRaises(ValueError):prepare(s,[r],t)
    def test_incomplete_source(self):
        with self.assertRaises(ValueError):prepare({**S,"sourceRows":2},[R],T)
    def test_archive_and_dedup(self):
        c=Client()
        with patch("listing_identity_r2.immutable_put",c.put):
            a=archive(c,S,[R],T,"2026-11-20T12:00:00+00:00");b=archive(c,S,[R],T,"2026-11-20T12:01:00+00:00")
        self.assertTrue(a["readbackVerified"]);self.assertEqual(b["storageStatus"],"already_present");self.assertEqual(len(c.data),3)
