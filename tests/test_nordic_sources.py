import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import nordic_sources as n
class NordicTests(unittest.TestCase):
 def test_rates_keep_zero_and_negative(self):
  self.assertEqual(n.dated_records([{"date":"2025-01","v":"-0.5"},{"date":"2025-02","v":0},{"date":"bad","v":1}],"date","v"),[{"date":"2025-01","value":-.5},{"date":"2025-02","value":0}])
 def test_conflicts_rejected(self):
  with self.assertRaises(ValueError):n.dated_records([{"date":"2025-01","v":1},{"date":"2025-01","v":2}],"date","v")
 def test_riksbank_series(self):
  u,p=n.riksbank("SECBREPOEFF","policy","percent",lambda u:[{"date":"2025-01-01","value":0}])
  self.assertIn("SECBREPOEFF",u);self.assertEqual(p["records"][0]["value"],0)

 def test_danish_jsonstat_v1(self):
  d={"dataset":{"dimension":{"id":["Tid"],"size":[1],"Tid":{"category":{"index":["2025M01"]}}},"value":[12]}}
  self.assertEqual(n.jsonstat(n.dk_jsonstat(d))["records"][0]["value"],12)
 def test_swedish_time_selector(self):
  def get(u):
   self.assertIn("statistikdatabasen.scb.se",u)
   self.assertIn("top%2824%29",u)
   return {"id":["Tid"],"size":[1],"dimension":{"Tid":{"category":{"index":["2025M01"]}}},"value":[3]}
  self.assertEqual(n.scb(get)[1]["records"][0]["value"],3)
 def test_mineral_csv_preserves_original_flags(self):
  from free_research import mineral_csv
  rows,cols=mineral_csv(b"year,quantity,unit\n2025,W,tonnes\n","mineral.csv","https://example.org")
  self.assertEqual(rows[0]["fields"]["quantity"],"W")
  self.assertEqual(cols,["year","quantity","unit"])
