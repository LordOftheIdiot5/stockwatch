import sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sec13f_figi_match import match
from sec13f_source import REQUIRED
F="BBG000BBJQV0"
BRIDGE={"records":[{"listingId":"XNAS:NVDA","status":"candidate","candidates":[{"figi":F,"compositeFIGI":F,"shareClassFIGI":"BBG001S5S399"}]}]}
def fixture(p,duplicate=False):
    h=["A","1","123456789",F,"100","2","SH","",""]
    option=["A","2","123456789",F,"200","3","SH","PUT","1"]
    with zipfile.ZipFile(p,"w") as z:
        for tab,rs in {"SUBMISSION":[["A","14-AUG-2026","13F-HR/A","1","30-JUN-2026"]],"COVERPAGE":[["A","RESTATEMENT","Manager","13F HOLDINGS REPORT"]],"INFOTABLE":[h,option,h if duplicate else ["A","3","123456789","","100","2","SH","",""]]}.items():
            z.writestr(tab+".tsv",chr(9).join(REQUIRED[tab].split())+chr(10)+chr(10).join(chr(9).join(r) for r in rs)+chr(10))
class MatchTests(unittest.TestCase):
    def test_match_separates_options_and_amendments(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.zip";fixture(p);x=match(p,BRIDGE)
            self.assertEqual(x["counts"]["matchedRows"],2)
            self.assertEqual(x["counts"]["shareRowsWithoutOption"],1)
            self.assertEqual(x["counts"]["optionRows"],1)
            self.assertEqual(x["counts"]["level:figi"],2)
            self.assertEqual(x["counts"]["level:compositeFIGI"],2)
            self.assertEqual(x["verifiedHoldings"],0)
    def test_duplicate_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.zip";fixture(p,True)
            with self.assertRaisesRegex(ValueError,"duplicate"):match(p,BRIDGE)
