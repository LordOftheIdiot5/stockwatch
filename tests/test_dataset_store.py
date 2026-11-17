import gzip,json,os,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import dataset_store as d
class DatasetStoreTests(unittest.TestCase):
 def sample(self):
  return {"id":"ssb-production","provider":"ssb","status":"ok","sourceUrl":"https://data.ssb.no/example","license":"CC BY 4.0","retrievedAt":"2026-11-17T00:00:00Z","records":[{"value":0,"period":"2025M01"}]}
 def test_content_addressing(self):
  x=self.sample();a=d.archive_objects(x);b=d.archive_objects({**x,"retrievedAt":"2026-11-18T00:00:00Z"})
  self.assertEqual(a[:2],b[:2]);self.assertNotEqual(a[2],b[2]);self.assertEqual(json.loads(gzip.decompress(a[1]))["records"],x["records"])
  self.assertNotEqual(d.archive_objects({**x,"records":[{"value":1}]})[0],a[0])
 def test_exclusions(self):
  for patch in ({"id":"yahoo"},{"status":"stale"},{"license":"unknown"},{"sourceUrl":"https://untrusted.example"},{"records":[]}):
   self.assertFalse(d.eligible({**self.sample(),**patch}))
  with self.assertRaises(PermissionError):d.archive(env={})
 def test_compact_index_not_copy(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/"data").mkdir();(root/"data/free-research.json").write_text(json.dumps({"datasets":[self.sample()],"restrictedSourceChecks":{"comtrade":{"secret":"never_copy"}}}))
   x=d.index(root);self.assertEqual(x["datasets"][0]["records"],1);self.assertNotIn("never_copy",str(x));self.assertNotIn("'value': 0",str(x))
   self.assertEqual(len(x["files"][0]["gitBlobSha"]),40)
