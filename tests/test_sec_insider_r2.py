import io,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sec_insider_evidence import write
from sec_insider_source import URL
from sec_insider_r2 import archive,prepare

CIK="0000001234"
META={"url":URL,"sha256":"a"*64,"bytes":123}
ROW={"accession":"0000001234-26-000001","table":"DERIV_TRANS","sourceRowKey":"1","form":"4","filingDate":"2026-01-02","transactionDate":"2026-01-01","code":"M","direction":"A","amendment":False,"filingUrl":"https://www.sec.gov/example"}
class Storage:
    def __init__(self):self.objects={};self.corrupt=False
    def put(self,client,body,key,metadata,content_type):
        if key in self.objects:
            if self.objects[key]!=body:raise ValueError("conflict")
            return "already_present"
        self.objects[key]=body
        return "created"
    def get_object(self,**kw):
        b=self.objects[kw["Key"]]
        return {"Body":io.BytesIO(b+b"x" if self.corrupt else b)}
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);write(self.root,{CIK:[ROW],"0000001235":[]},META)
    def test_readback_and_idempotence(self):
        s=Storage()
        with patch("sec_insider_r2.immutable_put",s.put):
            a=archive(s,self.root);b=archive(s,self.root)
        self.assertEqual(a["records"],1);self.assertEqual(a["created"],2)
        self.assertEqual(b["alreadyPresent"],2);self.assertTrue(b["readbackVerified"])
        self.assertEqual(a["receiptKey"],b["receiptKey"]);self.assertEqual(len(s.objects),3)
    def test_corrupt_readback_no_receipt(self):
        s=Storage();s.corrupt=True
        with patch("sec_insider_r2.immutable_put",s.put),self.assertRaises(ValueError):archive(s,self.root)
        self.assertFalse(any("/receipts/" in k for k in s.objects))
    def test_checksum_failure_before_writes(self):
        p=next(self.root.glob(CIK+"-*.json"));p.write_bytes(p.read_bytes()+b"x")
        s=Storage()
        with patch("sec_insider_r2.immutable_put",s.put),self.assertRaises(ValueError):archive(s,self.root)
        self.assertEqual(s.objects,{})
    def test_forbidden_owner_fields(self):
        write(self.root,{CIK:[{**ROW,"ownerName":"synthetic"}]},META)
        with self.assertRaises(ValueError):prepare(self.root)
    def test_duplicate_evidence(self):
        write(self.root,{CIK:[ROW,ROW]},META)
        with self.assertRaises(ValueError):prepare(self.root)
