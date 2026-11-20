import io,sys,unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from esma_delta_preflight import inspect,select,NS
def doc(body):
    return io.BytesIO(f'<Document xmlns="{NS[1:-1]}"><FinInstrmRptgRefDataDltaRpt>{body}</FinInstrmRptgRefDataDltaRpt></Document>'.encode())
def group(typ,day,complete=True):
    return {"type":typ,"date":day,"complete":complete,"expectedParts":1,"files":[{"name":"sample.zip"}]}
class DeltaPreflightTests(unittest.TestCase):
    def test_all_documented_actions(self):
        kinds=("NewRcrd","ModfdRcrd","TermntdRcrd","CancRcrd")
        xml="".join(f"<FinInstrm><{k}><Id>not retained</Id></{k}></FinInstrm>" for k in kinds)
        d=inspect(doc(xml));self.assertEqual(d["actionCounts"],{k:1 for k in kinds})
        self.assertNotIn("not retained",str(d))
    def test_empty_report_is_valid_unknown_action_fails(self):
        self.assertEqual(inspect(doc(""))["actionCounts"],{})
        with self.assertRaises(ValueError):inspect(doc("<FinInstrm><Unknown/></FinInstrm>"))
        with self.assertRaises(ValueError):inspect(io.BytesIO(b"<Document/>"))
    def test_manifest_gap_rejected(self):
        full=group("FULINS_E","2026-11-14");last=group("DLTINS","2026-11-16")
        with self.assertRaises(ValueError):select([full,last],date(2026,11,17))
        _,days,g=select([full,group("DLTINS","2026-11-15"),last],date(2026,11,17))
        self.assertEqual(len(days),2);self.assertEqual(g["date"],"2026-11-16")
