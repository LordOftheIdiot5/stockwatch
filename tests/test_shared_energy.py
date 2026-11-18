import unittest,sys,json,tempfile
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import shared_energy as s
class SharedEnergyTests(unittest.TestCase):
    def fixture(self):
        return {"schema_version":1,"source":s.SOURCE,"license":s.LICENSE,"generated":"2026-11-16T16:21:21+00:00","rows":[{"id":i,"zone":"NO"+str(i),"capacity_mw":10*i} for i in range(1,6)]+[{"id":6,"zone":"NO1","capacity_mw":None}]}
    def test_aggregate_and_license(self):
        d=s.parse(self.fixture())
        self.assertEqual(d["plants"],6)
        self.assertEqual(d["missingCapacity"],1)
        self.assertEqual(d["zones"][0]["capacityMW"],10)
        self.assertEqual(d["zones"][0]["capacityRecords"],1)
        with self.assertRaises(ValueError):s.parse({**self.fixture(),"license":"unknown"})
    def test_duplicate_rejected(self):
        d=self.fixture();d["rows"].append(d["rows"][0])
        with self.assertRaises(ValueError):s.parse(d)
    def test_outage_retains_snapshot(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);now=datetime(2026,11,19,tzinfo=timezone.utc)
            old=s.build(root,self.fixture,now)
            def fail():raise TimeoutError()
            new=s.build(root,fail,now+timedelta(days=1))
            self.assertEqual(new["zones"],old["zones"])
            self.assertEqual(new["sourceGenerated"],old["sourceGenerated"])
            self.assertEqual(new["refreshStatus"],"retained")
