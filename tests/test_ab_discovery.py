import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class ABDiscoveryTests(unittest.TestCase):
 def test_reference_candidates_have_distinct_source_identities(self):
    src=json.loads((ROOT/"data/instrument-directory.json").read_text())
    pairs=json.loads((ROOT/"data/ab-research-candidates.json").read_text())["records"]
    by={(r["mic"],r["figi"]):r for r in src["records"]}
    self.assertEqual(len(pairs),9)
    for p in pairs:
        self.assertEqual(p["priceStatus"],"not_connected")
        self.assertNotEqual(p["a"]["shareClassFIGI"],p["b"]["shareClassFIGI"])
        for k in ("a","b"):
            r=by[(p["mic"],p[k]["figi"])]
            self.assertEqual(r["name"],p[k]["name"])
            self.assertEqual(r["shareClassFIGI"],p[k]["shareClassFIGI"])
if __name__=="__main__":unittest.main()
