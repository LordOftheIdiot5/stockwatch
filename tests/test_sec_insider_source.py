import sys,tempfile,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sec_insider_source import inspect,REQUIRED
A="0000000001-26-000001"
def fixture(p,orphan=False):
    data={"SUBMISSION":[[A,"4","1"]],"NONDERIV_TRANS":[["0000000002-26-000001" if orphan else A,"1","Common stock","19-AUG-2026","P","A","2","20"],[A,"2","Common stock","19-AUG-2026","G","D","3","0"]],"DERIV_TRANS":[[A,"1","19-AUG-2026","M","A"]]}
    with zipfile.ZipFile(p,"w") as z:
        for name,rs in data.items():
            z.writestr(name+".tsv",chr(9).join(REQUIRED[name].split())+chr(10)+chr(10).join(chr(9).join(x) for x in rs)+chr(10))
class InsiderTests(unittest.TestCase):
    def test_code_and_exact_issuer(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.zip";fixture(p)
            r=inspect(p,{"0000000001"})
            self.assertEqual(r["matchedIssuers"],1);self.assertEqual(r["counts"]["matchedReportedPurchaseRows"],1)
            self.assertEqual(r["counts"]["matched:DERIV_TRANS"],1);self.assertEqual(r["publishedTransactions"],0)
            self.assertEqual(inspect(p,{"0000000002"})["matchedIssuers"],0)
    def test_orphan_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.zip";fixture(p,True)
            with self.assertRaises(ValueError):inspect(p,{"0000000001"})
