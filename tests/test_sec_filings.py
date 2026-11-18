import sys,json,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import sec_filings as s
NOW=datetime(2026,11,19,12,tzinfo=timezone.utc)
SEED={"cik":"0001045810","symbol":"NVDA","mic":"XNAS","name":"NVIDIA","sector":"Technology","identityStatus":"sec_ticker_exchange_association"}
def sample():
    return {"cik":"1045810","tickers":["NVDA"],"exchanges":["Nasdaq"],"filings":{"recent":{
        "accessionNumber":["0001045810-26-000001","0001045810-26-000002","bad","0001045810-26-000003"],
        "form":["10-Q","4","8-K","10-K"],
        "acceptanceDateTime":["2026-11-18T20:01:00Z"]*3+["2026-11-20T20:01:00Z"],
        "filingDate":["2026-11-18"]*3+["2026-11-20"]}}}
class SecTests(unittest.TestCase):
    def test_exact_filer_and_listing(self):
        rows=s.parse(SEED,sample(),NOW)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["sourceIssuer"],SEED["cik"])
        self.assertEqual(rows[0]["match"],"issuer_code")
        self.assertEqual(rows[0]["published"],"2026-11-18T20:01:00Z")
        self.assertNotIn("price",rows[0])
        self.assertIn("000104581026000001",rows[0]["url"])
        with self.assertRaises(ValueError):s.parse(SEED,{**sample(),"tickers":["OTHER"]},NOW)
        with self.assertRaises(ValueError):s.parse(SEED,{**sample(),"cik":123},NOW)
    def test_daily_limit_and_retention(self):
        from datetime import timedelta
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/"data").mkdir()
            (root/"data/us-equity-seed.json").write_text(json.dumps({"records":[SEED]}))
            calls=[]
            def fetch(cik,agent):calls.append(cik);return sample()
            a=s.build(root,NOW,fetch,lambda _:None,agent="Nordl contact@example.com")
            self.assertEqual(len(a["items"]),1)
            s.build(root,NOW,fetch,lambda _:None,agent="Nordl contact@example.com")
            self.assertEqual(len(calls),1)
            def fail(*a):raise TimeoutError()
            b=s.build(root,NOW+timedelta(days=1),fail,lambda _:None,agent="Nordl contact@example.com")
            self.assertEqual(b["items"],a["items"])
            self.assertEqual(b["issuers"][SEED["cik"]]["status"],"error")
            self.assertEqual(b["issuers"][SEED["cik"]]["lastSuccess"],a["issuers"][SEED["cik"]]["lastSuccess"])

    def test_distinct_filings_are_not_duplicate_generic_form_titles(self):
        from news_quality import annotate
        row=s.parse(SEED,sample(),NOW)[0]
        second={**row,"id":"sec:second","sourceAccession":"0001045810-26-000004"}
        self.assertTrue(all(not x.get("duplicateOf") for x in annotate([row,second])))
