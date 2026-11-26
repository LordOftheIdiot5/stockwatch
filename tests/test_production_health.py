import sys,unittest,json,tempfile
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from production_health import audit,BASE,API
class HealthTests(unittest.TestCase):
    def run_fixture(self,drop=False,noindex=False,now=None,**kwargs):
        rows=[{"id":str(i),"group":"monitored" if i<139 else "target","priceStatus":"scanner" if i<(151 if drop else 152) and not(drop and i==0) else "missing"} for i in range(500)]
        n=sum(r["priceStatus"]!="missing" for r in rows)
        def get(url):
            p=url.removeprefix(BASE)
            if url==API:return json.dumps({"status":"ok","storage":"d1","articles":1640}),{}
            if p=="robots.txt":return "User-agent: *\nSitemap: "+BASE+"sitemap.xml",{}
            if p=="sitemap.xml":return "<urlset>"+"".join("<url><loc>"+BASE+x+"</loc></url>" for x in [""]+[str(i) for i in range(16)])+"</urlset>",{}
            if p=="data/listing-coverage-v1.json":return json.dumps({"summary":{"listings":500,"priced":n,"missingPrice":500-n},"records":rows}),{}
            if p=="data/signals.json":return json.dumps({"generated":"2026-11-19T21:00:00Z","companies":[{}]*139}),{}
            if p=="data/source-health.json":return json.dumps({"priceFreshness":{"status":"coverage_ok"}}),{}
            return '<html><head><link rel="canonical" href="'+BASE+p.split("?")[0]+'"></head><body>Company research</body></html>',{"x-robots-tag":"noindex"} if noindex else {}
        return audit(get,now or datetime(2026,11,19,22,tzinfo=timezone.utc),**kwargs)
    def test_known_gap_not_incident(self):
        d=self.run_fixture();self.assertEqual(d["status"],"ok");self.assertEqual(d["metrics"]["knownPriceGap"],348)
    def test_loss_of_prices_incident(self):
        d=self.run_fixture(drop=True);self.assertEqual(d["status"],"critical");self.assertIn("monitored_price_missing",[x["code"] for x in d["issues"]])
    def test_http_noindex_detected(self):
        self.assertEqual(self.run_fixture(noindex=True)["status"],"critical")

    def test_overdue_weekday_scan_warns_even_if_pages_load(self):
        d=self.run_fixture(now=datetime(2026,11,20,11,tzinfo=timezone.utc))
        self.assertEqual(d["status"],"degraded")
        self.assertIn("market_scan_overdue",[x["code"] for x in d["issues"]])
    def test_weekend_refresh_warning_after_coverage_window(self):
        d=self.run_fixture(now=datetime(2026,11,21,18,tzinfo=timezone.utc))
        self.assertEqual(d["status"],"degraded")
        self.assertIn("weekend_scan_overdue",[x["code"] for x in d["issues"]])
    def test_overnight_snapshot_not_falsely_overdue(self):
        d=self.run_fixture(now=datetime(2026,11,20,2,tzinfo=timezone.utc))
        self.assertNotIn("market_scan_overdue",[x["code"] for x in d["issues"]])

    def mapping_fixture(self,root,missing=False,mismatch=False):
        folder=Path(root)/"data/gleif-isin-lei"
        folder.mkdir(parents=True)
        date="2026-11-19"
        digest="a"*64
        name=date+"-"+digest[:16]+".json"
        counts={"matchedISINs":17,"ambiguousISINs":0,"eligibleISINs":18}
        idx={"schemaVersion":1,"status":"ok","lastSuccess":"2026-11-19T21:00:00Z","sourceDate":date,
             "snapshot":"data/gleif-isin-lei/"+name,**counts}
        snap={"schemaVersion":1,"source":"ANNA/GLEIF","sourceDate":date,"sha256":digest,**counts,
              "records":[{"isin":str(i),"status":"matched" if i<17 else "unmatched"} for i in range(18)]}
        if mismatch:snap["matchedISINs"]=16
        (folder/"index.json").write_text(json.dumps(idx),encoding="utf-8")
        if not missing:(folder/name).write_text(json.dumps(snap),encoding="utf-8")
    def test_internal_gleif_not_a_public_endpoint(self):
        with tempfile.TemporaryDirectory() as d:
            self.mapping_fixture(d)
            result=self.run_fixture(require_gleif=True,local_root=Path(d))
            self.assertEqual(result["status"],"ok")
            self.assertEqual(result["metrics"]["gleifMatched"],17)
            self.assertIn({"id":"gleif_internal_snapshot","ok":True},result["checks"])
            self.assertNotIn("gleif_index",[x["id"] for x in result["checks"]])
    def test_internal_gleif_missing_or_inconsistent_is_critical(self):
        for kw in ({"missing":True},{"mismatch":True}):
            with self.subTest(kw=kw),tempfile.TemporaryDirectory() as d:
                self.mapping_fixture(d,**kw)
                result=self.run_fixture(require_gleif=True,local_root=Path(d))
                self.assertEqual(result["status"],"critical")
                self.assertIn("gleif_internal_snapshot",[x["code"] for x in result["issues"]])
    def test_internal_gleif_retained_age_warns(self):
        with tempfile.TemporaryDirectory() as d:
            self.mapping_fixture(d)
            result=self.run_fixture(require_gleif=True,local_root=Path(d),now=datetime(2026,11,23,2,tzinfo=timezone.utc))
            self.assertIn("gleif_refresh",[x["code"] for x in result["issues"]])
