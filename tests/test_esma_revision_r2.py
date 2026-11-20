import hashlib,io,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from esma_revision_r2 import archive,prepare,RIGHTS,DOCS,encode
DAY="2026-11-19"
class Storage:
    def __init__(self):self.objects={};self.bad=False
    def put(self,client,body,key,metadata,content_type):
        if key in self.objects:
            if self.objects[key]!=body:raise ValueError("conflict")
            return "already_present"
        self.objects[key]=body
        return "created"
    def get_object(self,**kw):return {"Body":io.BytesIO(self.objects[kw["Key"]]+(b"x" if self.bad else b""))}
class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        d={"schemaVersion":1,"source":"ESMA FIRDS","sourceUrl":DOCS,"sourceRights":RIGHTS,"publicationFileDate":DAY,"records":[{"action":"ModfdRcrd"}],"parts":[{}],"sourceActionCounts":{"ModfdRcrd":100},"matchedEvents":1}
        raw=encode(d);digest=hashlib.sha256(raw).hexdigest();self.path=self.root/(DAY+"-"+digest+".json");self.path.write_bytes(raw)
        self.idx={"status":"ok","baselineDate":"2026-11-18","throughDate":DAY,"matchedEvents":1,"sourceActionCounts":{"ModfdRcrd":100},"currentStateEstablished":False,"replayComplete":False,"consolidatedCancellationReconciled":False,"days":[{"date":DAY,"path":"data/esma-delta-history/"+self.path.name,"sha256":digest,"matchedEvents":1,"sourceActions":100,"sourceParts":1}]}
        self.save()
    def save(self): (self.root/"index.json").write_bytes(encode(self.idx))
    def test_readback_and_idempotence(self):
        s=Storage()
        with patch("esma_revision_r2.immutable_put",s.put):
            a=archive(s,self.root);b=archive(s,self.root)
        self.assertEqual(a["matchedEventsRetained"],1);self.assertEqual(a["sourceActionsScanned"],100)
        self.assertEqual(b["alreadyPresent"],1);self.assertEqual(a["receiptKey"],b["receiptKey"])
        self.assertEqual(len(s.objects),2)
    def test_corruption_no_receipt(self):
        s=Storage();s.bad=True
        with patch("esma_revision_r2.immutable_put",s.put),self.assertRaises(ValueError):archive(s,self.root)
        self.assertFalse(any("/receipts/" in k for k in s.objects))
    def test_bad_hash_before_write(self):
        self.path.write_bytes(self.path.read_bytes()+b"x")
        with self.assertRaises(ValueError):prepare(self.root)
    def test_missing_day_and_unverified_claim(self):
        self.idx["baselineDate"]="2026-11-17";self.save()
        with self.assertRaises(ValueError):prepare(self.root)
        self.idx["baselineDate"]="2026-11-18";self.idx["currentStateEstablished"]=True;self.save()
        with self.assertRaises(ValueError):prepare(self.root)
    def test_count_mismatch(self):
        self.idx["matchedEvents"]=2;self.save()
        with self.assertRaises(ValueError):prepare(self.root)
