import io,json,tempfile,unittest,zipfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import delayed_exchange as d
def fixture():
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:z.writestr("Trades_Equities.csv","Copyright fixture\n"+",".join(sorted(d.REQUIRED))+"\n")
    return b.getvalue()
class DelayedExchangeTests(unittest.TestCase):
    def test_schema(self):
        self.assertTrue(d.csv_schema(fixture())["schemaValidated"])
        with self.assertRaises(zipfile.BadZipFile):d.csv_schema(b"<html>")
    def test_safe_urls(self):
        self.assertTrue(d.eur_url("OSL","PREVIOUS_TRADING_DAY").endswith("/OSL"))
        with self.assertRaises(ValueError):d.eur_url("../bad","PREVIOUS_TRADING_DAY")
        raw=b'<a href="/download/NordicEquity-posttrade-2026-01-02T1200">file</a><a href="https://evil.invalid/NordicEquity-posttrade">external</a>'
        self.assertEqual(len(d.nasdaq_links(raw)),1)
    def test_probe_no_public_data(self):
        def fetch(url,*args):return fixture() if url.startswith(d.EUR) else b"<html></html>"
        r=d.probe(fetch=fetch)
        self.assertEqual(r["euronext"]["status"],"schema_validated")
        self.assertFalse(r["publicPublication"])
        self.assertFalse(r["nasdaq"]["tradeDownloadEnabled"])
    def test_private_archive(self):
        with tempfile.TemporaryDirectory() as root:
            name=d.private_save(fixture(),root,"euronext")
            self.assertTrue((Path(root)/"euronext"/name).is_file())
        with self.assertRaises(ValueError):d.private_save(b"x",d.ROOT/"data","euronext")
if __name__=="__main__":unittest.main()
