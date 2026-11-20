import sys,unittest,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from esef_ifrs_fact_pilot import inspect,LEI
def fixture():
    return {"documentInfo":{"documentType":"https://xbrl.org/2021/xbrl-json","namespaces":{"i":"https://xbrl.ifrs.org/taxonomy/2025-03-27/ifrs-full","l":"http://standards.iso.org/iso/17442","u":"http://www.xbrl.org/2003/iso4217"}},"facts":{"f1":{"value":"100","decimals":0,"dimensions":{"concept":"i:Assets","entity":"l:"+LEI,"unit":"u:EUR","period":"2026-01-01T00:00:00"}},"f2":{"value":"80","dimensions":{"concept":"i:Revenue","entity":"l:"+LEI,"unit":"u:EUR","period":"2025-01-01T00:00:00/2026-01-01T00:00:00"}}}}
class FactPilotTests(unittest.TestCase):
    def test_reporting_boundary_and_annual_duration(self):
        d=fixture();self.assertEqual(len(inspect(d)),2)
        d["facts"]["f2"]["dimensions"]["period"]="2025-07-01T00:00:00/2026-01-01T00:00:00"
        self.assertEqual(len(inspect(d)),1)
    def test_extra_dimensions_and_wrong_entity(self):
        d=fixture();d["facts"]["f1"]["dimensions"]["i:Segment"]="i:Other"
        d["facts"]["f2"]["dimensions"]["entity"]="l:OTHER"
        with self.assertRaises(ValueError):inspect(d)
    def test_duplicate_conflict_not_summed(self):
        d=fixture();d["facts"]["f3"]=copy.deepcopy(d["facts"]["f1"]);d["facts"]["f3"]["value"]="101"
        x=inspect(d);a=next(r for r in x if r["concept"]=="Assets")
        self.assertEqual(a["status"],"conflicting");self.assertEqual(len(a["facts"]),2)
