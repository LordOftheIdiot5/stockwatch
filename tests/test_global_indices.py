import sys,unittest,tempfile,json
from datetime import date,datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from global_indices import parse,build
ROW={"Date":"1151119","TAIEX":"38426.89","Change":"-1768.02"}
class IndexTests(unittest.TestCase):
    def test_roc_date_and_percent(self):
        x=parse([ROW],date(2026,11,20))[0];self.assertEqual(x["date"],"2026-11-19");self.assertAlmostEqual(x["changePct"],-4.398616,places=4)
    def test_future_and_conflicts(self):
        with self.assertRaises(ValueError):parse([ROW],date(2026,11,18))
        with self.assertRaises(ValueError):parse([ROW,dict(ROW,TAIEX="1")],date(2026,11,20))
    def test_retention(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);a=build(root,datetime(2026,11,20,7,tzinfo=timezone.utc),lambda:[ROW])
            def fail():raise TimeoutError()
            with self.assertRaises(TimeoutError):build(root,datetime(2026,11,21,7,tzinfo=timezone.utc),fail)
            b=json.loads((root/"data/global-indices-v1.json").read_text());self.assertEqual(b["latest"],a["latest"]);self.assertEqual(b["status"],"retained_after_error")

    def test_bootstrap_before_close_and_refresh_after_close(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            a=build(root,datetime(2026,11,20,1,tzinfo=timezone.utc),lambda:[ROW])
            self.assertEqual(a["latest"]["date"],"2026-11-19")
            b=build(root,datetime(2026,11,20,7,tzinfo=timezone.utc),lambda:[ROW,dict(ROW,Date="1151120")])
            self.assertEqual(b["latest"]["date"],"2026-11-20")
