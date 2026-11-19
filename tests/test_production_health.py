import sys,unittest,json
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from production_health import audit,BASE,API
class HealthTests(unittest.TestCase):
    def run_fixture(self,drop=False,noindex=False):
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
            return '<html><head><link rel="canonical" href="'+BASE+p.split("?")[0]+'"></head></html>',{"x-robots-tag":"noindex"} if noindex else {}
        return audit(get,datetime(2026,11,19,22,tzinfo=timezone.utc))
    def test_known_gap_not_incident(self):
        d=self.run_fixture();self.assertEqual(d["status"],"ok");self.assertEqual(d["metrics"]["knownPriceGap"],348)
    def test_loss_of_prices_incident(self):
        d=self.run_fixture(drop=True);self.assertEqual(d["status"],"critical");self.assertIn("monitored_price_missing",[x["code"] for x in d["issues"]])
    def test_http_noindex_detected(self):
        self.assertEqual(self.run_fixture(noindex=True)["status"],"critical")
