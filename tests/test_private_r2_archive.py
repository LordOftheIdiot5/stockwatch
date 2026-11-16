import io,zipfile,unittest,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import private_r2_archive as m
import delayed_exchange as ex
class Exists(Exception):
    response={"ResponseMetadata":{"HTTPStatusCode":412}}
class FakeR2:
    def __init__(self):self.objects={}
    def put_object(self,**kw):
        assert kw["IfNoneMatch"]=="*"
        key=kw["Key"]
        if key in self.objects:raise Exists()
        self.objects[key]=kw
    def head_object(self,**kw):
        x=self.objects[kw["Key"]]
        return {"Metadata":x["Metadata"],"ContentLength":len(x["Body"])}
def fixture(value="1"):
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:
        z.writestr("Trades.csv",",".join(sorted(ex.REQUIRED))+"\n"+value+"\n")
    return b.getvalue()
class ArchiveTests(unittest.TestCase):
    def test_config_defaults_closed(self):
        with self.assertRaises(ValueError):m.configuration({})
        env={"STOCKWATCH_R2_RETENTION_APPROVED":"true","STOCKWATCH_R2_ACCOUNT_ID":"a"*32,
             "STOCKWATCH_R2_BUCKET":m.BUCKET,"STOCKWATCH_R2_ACCESS_KEY_ID":"fixture",
             "STOCKWATCH_R2_SECRET_ACCESS_KEY":"fixture"}
        self.assertEqual(m.configuration(env),"a"*32)
        pending={**env,"STOCKWATCH_R2_RETENTION_APPROVED":"false"}
        with self.assertRaises(ValueError):m.configuration(pending)
        self.assertEqual(m.configuration(pending,smoke_only=True),"a"*32)
        with self.assertRaises(ValueError):m.configuration({},smoke_only=True)
        with self.assertRaises(ValueError):m.configuration({**pending,"STOCKWATCH_R2_BUCKET":"public"},smoke_only=True)
        with self.assertRaises(ValueError):m.configuration({**env,"STOCKWATCH_R2_BUCKET":"public"})
    def test_dedup_and_revision_preservation(self):
        s=FakeR2();raw=fixture()
        now=datetime(2025,1,3,tzinfo=timezone.utc)
        self.assertEqual(m.archive(s,"OSL","CURRENT_TRADING_DAY",lambda _:raw,now),"created")
        self.assertEqual(m.archive(s,"OSL","PREVIOUS_TRADING_DAY",lambda _:raw,now),"already_present")
        self.assertEqual(len([k for k in s.objects if k.endswith(".zip")]),1)
        self.assertEqual(len([k for k in s.objects if k.endswith(".json")]),2)
        self.assertEqual(m.archive(s,"OSL","CURRENT_TRADING_DAY",lambda _:fixture("2"),now),"created")
        self.assertEqual(len([k for k in s.objects if k.endswith(".zip")]),2)
    def test_invalid_archive_never_written(self):
        s=FakeR2()
        with self.assertRaises(zipfile.BadZipFile):
            m.archive(s,"OSL","CURRENT_TRADING_DAY",lambda _:b"<html>")
        self.assertEqual(s.objects,{})
    def test_integrity_conflict(self):
        s=FakeR2()
        m.immutable_put(s,b"old","key",{},"text/plain")
        with self.assertRaises(ValueError):m.immutable_put(s,b"new","key",{},"text/plain")
if __name__=="__main__":unittest.main()
