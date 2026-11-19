import io,sys,unittest,zipfile,tempfile,json
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from gleif_isin_lei import inspect,valid_lei,build
ISIN="NO0005052605"
LEI="5493001KJTIIGC8Y1R12"
def archive(text):
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:z.writestr("mapping.csv",text)
    return b.getvalue()
class GLEIFTests(unittest.TestCase):
    def test_checksum_and_exact_match(self):
        self.assertTrue(valid_lei(LEI))
        d=inspect(archive("ISIN,LEI\n"+ISIN+","+LEI+"\n"+ISIN+","+LEI+"\n"),{ISIN:{"NHY.OL"},"US0378331005":{"AAPL"}})
        self.assertEqual(d["matchedISINs"],1);self.assertEqual(d["eligibleISINs"],2)
        self.assertEqual(next(r for r in d["records"] if r["isin"]==ISIN)["leis"],[LEI])
    def test_invalid_schema(self):
        with self.assertRaises(ValueError):inspect(archive("Ticker,Name\nA,Alpha\n"),{ISIN:{"x"}})
    def test_failure_retains_prior(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"data").mkdir()
            (root/"data/listing-coverage-v1.json").write_text(json.dumps({"records":[{"id":"a","isin":ISIN}]}))
            day=datetime(2026,11,19,tzinfo=timezone.utc)
            first=build(root,day,fetch=lambda url:archive("ISIN,LEI\n"+ISIN+","+LEI+"\n"))
            def fail(url):raise TimeoutError()
            with self.assertRaises(TimeoutError):build(root,datetime(2026,11,20,tzinfo=timezone.utc),fetch=fail)
            saved=json.loads((root/"data/gleif-isin-lei/index.json").read_text())
            self.assertEqual(saved["snapshot"],first["snapshot"])
            self.assertEqual(saved["status"],"retained_after_error")
