import io,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from test_sec13f_figi_match import fixture,BRIDGE
from sec13f_figi_match import match
from sec13f_candidate_r2 import archive,prepare
from sec13f_source import URL
META={"url":URL,"sha256":"a"*64,"bytes":123}
STAMP="2026-11-20T01:00:00+00:00"
class Storage:
    def __init__(self):self.objects={};self.bad=False
    def put(self,client,body,key,metadata,content_type):
        if key in self.objects:
            if self.objects[key]!=body:raise ValueError("conflict")
            return "already_present"
        self.objects[key]=body
        return "created"
    def get_object(self,**kw):
        return {"Body":io.BytesIO(self.objects[kw["Key"]]+(b"x" if self.bad else b""))}
class ArchiveTests(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.zip";fixture(p);self.records=[];self.summary=match(p,BRIDGE,self.records.append)
    def test_candidate_evidence_preserves_units_and_options(self):
        a,b=self.records
        self.assertEqual(a["reportedValue"],"100");self.assertEqual(a["valueUnit"],"USD")
        self.assertEqual(b["putCall"],"PUT");self.assertTrue(b["otherManagerReferencePresent"])
        self.assertFalse(a["historicalIdentityVerified"]);self.assertNotIn("cusip",a)
        self.assertEqual(a["amendmentType"],"RESTATEMENT")
    def test_readback_and_idempotence(self):
        s=Storage()
        with patch("sec13f_candidate_r2.immutable_put",s.put):
            a=archive(s,self.records,self.summary,META,STAMP)
            b=archive(s,self.records,self.summary,META,STAMP)
        self.assertEqual(a["candidateRows"],2);self.assertEqual(a["verifiedHoldings"],0)
        self.assertEqual(b["alreadyPresent"],1);self.assertTrue(b["readbackVerified"])
        self.assertEqual(a["receiptKey"],b["receiptKey"]);self.assertEqual(len(s.objects),2)
    def test_corruption_no_receipt(self):
        s=Storage();s.bad=True
        with patch("sec13f_candidate_r2.immutable_put",s.put),self.assertRaises(ValueError):
            archive(s,self.records,self.summary,META,STAMP)
        self.assertFalse(any("/receipts/" in k for k in s.objects))
    def test_count_and_identity_guards(self):
        with self.assertRaises(ValueError):prepare(self.records[:1],self.summary,META,STAMP)
        self.records[0]["historicalIdentityVerified"]=True
        with self.assertRaises(ValueError):prepare(self.records,self.summary,META,STAMP)
    def test_duplicates_and_unexpected_fields(self):
        with self.assertRaises(ValueError):prepare([self.records[0]]*2,self.summary,META,STAMP)
        self.records[0]["managerName"]="Synthetic"
        with self.assertRaises(ValueError):prepare(self.records,self.summary,META,STAMP)
