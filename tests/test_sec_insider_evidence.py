import sys,tempfile,unittest,zipfile,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sec_insider_evidence import extract,write,amount
from sec_insider_source import REQUIRED
A="0000000001-26-000001"
class EvidenceTests(unittest.TestCase):
    def test_evidence_and_idempotence(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/"source.zip"
            with zipfile.ZipFile(p,"w") as z:
                for table,data in {"SUBMISSION":[A,"4/A","1","20-AUG-2026"],"NONDERIV_TRANS":[A,"1","Common stock","19-AUG-2026","P","A","2","20"],"DERIV_TRANS":[A,"1","19-AUG-2026","M","A"]}.items():
                    h=REQUIRED[table]+(" FILING_DATE" if table=="SUBMISSION" else "")
                    z.writestr(table+".tsv",chr(9).join(h.split())+chr(10)+chr(9).join(data)+chr(10))
            r=extract(p,{"0000000001","0000000002"})
            self.assertEqual(len(r["0000000001"]),2);self.assertEqual(r["0000000002"],[])
            self.assertTrue(r["0000000001"][0]["amendment"])
            a=write(root/"out",r,{"sha256":"test"});b=write(root/"out",r,{"sha256":"test"})
            self.assertEqual(a,b);self.assertEqual(a["records"],2);self.assertEqual(a["publishedTransactions"],0)
    def test_amount(self):
        self.assertIsNone(amount(""));self.assertEqual(amount("0"),"0")
        with self.assertRaises(ValueError):amount("NaN")
