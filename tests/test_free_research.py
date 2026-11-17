import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import free_research as f
class FreeResearchTests(unittest.TestCase):
 def test_sparse_json_stat_no_zero_fill(self):
  d={"id":["geo","time"],"size":[2,2],"dimension":{"geo":{"category":{"index":{"NO":0,"SE":1}}},"time":{"category":{"index":["2025-01","2025-02"]}}},"value":{"0":12,"3":0},"status":{"3":"p"}}
  r=f.jsonstat(d)["records"];self.assertEqual(len(r),2);self.assertEqual(r[-1]["value"],0);self.assertEqual(r[-1]["status"],"p")
 def test_arcgis_duplicate_fails(self):
  with self.assertRaises(ValueError):f.sodir(lambda u:{"features":[{"attributes":{"id":1}},{"attributes":{"id":1}}]},1,["id"],"id")
 def test_sec_filings_preserve_units_and_dates(self):
  item={"val":12,"form":"10-Q","start":"2025-01-01","end":"2025-03-31","filed":"2025-05-01","accn":"0001045810-25-000001"}
  data={"cik":1045810,"facts":{"us-gaap":{"NetIncomeLoss":{"units":{"USD":[item,{**item,"filed":"2027-01-01"}]}}}}}
  self.assertEqual(len(f.sec_facts(data,"0001045810","2026-11-17")["records"]),1)
  with self.assertRaises(ValueError):f.sec_facts(data,"0000001234")
 def test_comtrade_probe_never_returns_values(self):
  x=f.comtrade_probe(lambda u:{"data":[{"reporterCode":276,"period":"2025","partnerCode":0,"cmdCode":"8703","flowCode":"X","primaryValue":12345}]})
  self.assertEqual(x["matchedRows"],1);self.assertNotIn("12345",str(x))
