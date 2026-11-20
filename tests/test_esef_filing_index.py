import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from esef_filing_index import inspect
LEI="549300W1OGQF5LZIH349"
def fixture():
    return {"meta":{"count":1},"included":[{"type":"entity","id":"1","attributes":{"identifier":LEI}}],"data":[{"type":"filing","id":"2","relationships":{"entity":{"data":{"id":"1"}}},"attributes":{"period_end":"2025-12-31","country":"NO","json_url":"/example.json","error_count":0}}]}
class Tests(unittest.TestCase):
    def test_exact_match_and_metadata(self):
        x=inspect(fixture(),{LEI:{"MOWI"}})
        self.assertEqual(x["matchedLEIs"],1);self.assertEqual(x["matchedFilingsWithJSON"],1);self.assertEqual(x["financialFactsPublished"],0)
        self.assertEqual(inspect(fixture(),{"other":set()})["matchedLEIs"],0)
    def test_incomplete_and_orphan(self):
        d=fixture();d["meta"]["count"]=2
        with self.assertRaises(ValueError):inspect(d,{})
        d=fixture();d["included"]=[]
        with self.assertRaises(ValueError):inspect(d,{})
