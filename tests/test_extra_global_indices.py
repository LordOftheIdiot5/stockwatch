import sys,tempfile,unittest,json
from datetime import datetime,date,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from extra_global_indices import parse,build,SOURCES
T=[{"Date":"20261118","Close":"307.55","Change":"0.94"},{"Date":"20261119","Close":"285.33","Change":"-22.22"}]
F=[{"Date":"1151118","FormosaIndex":"44216.00"},{"Date":"1151119","FormosaIndex":"42194.32"}]
class ExtraIndexTests(unittest.TestCase):
    def test_tpex(self):
        x=parse(SOURCES["tpex"],T,date(2026,11,20))
        self.assertAlmostEqual(x[-1]["changePct"],-7.224842,places=4)
    def test_formosa(self):
        x=parse(SOURCES["formosa"],F,date(2026,11,20))
        self.assertIsNone(x[0]["changePct"]);self.assertAlmostEqual(x[1]["changePct"],-4.57228,places=4)
    def test_gap_no_daily_return(self):
        x=parse(SOURCES["formosa"],[F[0],dict(F[1],Date="1151125")],date(2026,11,25))
        self.assertIsNone(x[-1]["changePct"])
    def test_provider_failure_retains_and_does_not_block_other(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);now=datetime(2026,11,20,7,tzinfo=timezone.utc)
            def get(s):return T if s["key"]=="tpex:TPEx" else F
            a=build(root,now,get)
            def fail(s):
                if s["key"]=="tpex:TPEx":raise TimeoutError()
                return F
            with self.assertRaises(RuntimeError):build(root,datetime(2026,11,21,7,tzinfo=timezone.utc),fail)
            b=json.loads((root/"data/global-index-tpex.json").read_text())
            self.assertEqual(b["latest"],a["tpex"]["latest"]);self.assertEqual(b["status"],"retained_after_error")
