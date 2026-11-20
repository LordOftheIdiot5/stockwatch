import sys,unittest,tempfile,zipfile
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sec13f_source import inspect,unit,REQUIRED
def fixture(p,orphan=False):
    with zipfile.ZipFile(p,"w") as z:
        for tab,vals in {"SUBMISSION":["A","14-AUG-2026","13F-HR/A","1","30-JUN-2026"],"COVERPAGE":["A","RESTATEMENT","Manager","13F HOLDINGS REPORT"],"INFOTABLE":["B" if orphan else "A","1","123456789","","100","2","SH","",""]}.items():
            z.writestr(tab+".tsv",chr(9).join(REQUIRED[tab].split())+chr(10)+chr(9).join(vals)+chr(10))
class Tests(unittest.TestCase):
    def test_units(self):
        self.assertEqual(unit(date(2023,1,2)),"thousand USD")
        self.assertEqual(unit(date(2023,1,3)),"USD")
    def test_join(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.zip";fixture(p)
            self.assertEqual(inspect(p)["counts"]["sharesWithoutOption"],1)
            self.assertEqual(inspect(p)["amendments"],{"RESTATEMENT":1})
            fixture(p,True)
            with self.assertRaisesRegex(ValueError,"orphan"):inspect(p)
