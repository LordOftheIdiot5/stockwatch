import importlib.util,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location("verify_pages_release",ROOT/"scripts/verify_pages_release.py")
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_bounded_eventual_consistency(self):
        with tempfile.TemporaryDirectory() as d:
            prior=m.ROOT
            try:
                m.ROOT=Path(d)
                for p in m.PATHS:
                    (m.ROOT/p).parent.mkdir(parents=True, exist_ok=True)
                    (m.ROOT/p).write_bytes(("<html>"+p+"</html>").encode())
                attempts=[]
                def fetch(p,n):
                    attempts.append((p,n))
                    return b"stale" if n==1 else (m.ROOT/p).read_bytes()
                result=m.check(attempts=2,interval=0,fetch=fetch,probe=lambda p,n:404)
                self.assertTrue(all(x["match"] for x in result.values()))
                self.assertEqual(len(attempts),2*len(m.PATHS))
            finally:m.ROOT=prior
    def test_rejects_stale_content(self):
        with tempfile.TemporaryDirectory() as d:
            prior=m.ROOT
            try:
                m.ROOT=Path(d)
                for p in m.PATHS:
                    (m.ROOT/p).parent.mkdir(parents=True, exist_ok=True)
                    (m.ROOT/p).write_text(p)
                with self.assertRaisesRegex(RuntimeError,"do not match"):
                    m.check(attempts=1,interval=0,fetch=lambda p,n:b"wrong",probe=lambda p,n:404)
            finally:m.ROOT=prior
    def test_v98_new_css_and_v97_source_health_assets_are_deploy_verified(self):
        for path in ("index.html","v4.js","overview-parity-v98.css","overview-target-v110.css","overview-firstfold-v116.css","news-compact-v116.css","workspace-density-v110b.css","workspace-density-v110b.js","overview-structure-v110d.css","overview-structure-v110d.js","overview-geo-v110e.css","overview-geo-v110e.js","brand/world-land-ne110.svg","directory.html","research.html","search.html","data-products.html","brand/data-portal.js","brand/data-portal.css","welcome.html","brand/workspace-navigation-v112.css","brand/workspace-navigation-v112.js",
                     "company-cockpit-v110c.css","company-cockpit-v110c.js","company-workflow-v113.js","core-research-v113.css","native-chart.js","terminal.js","secondary-markets-v114.js","secondary-markets-v114.css","calendar.html","shipping.html","spreads.html","commodities.html","shorts.html","compare.html","spreads.html",
                     "nasdaq-notices-v100.js","nasdaq-notices-v100.css","news.html",
                     "global-market-pulse.js","heatmap-experience-v93.js",
                     "overview-watchlist-v99.js","overview-watchlist-v99.css",
                     "health.html","price-evidence-v97.js","price-evidence-v97.css"):
            self.assertIn(path,m.PATHS)
        self.assertEqual(len(m.PATHS),len(set(m.PATHS)))
    def test_v119c_high_detail_shipping_assets_are_part_of_production_parity(self):
        for path in ("shipping.html","shipping-atlas-v118.js",
                     "shipping-mapfirst-v119.js","shipping-mapfirst-v119.css",
                     "shipping-map-polish-v119b.css",
                     "brand/world-land-ne50-v119c.svg",
                     "brand/world-borders-ne50-v119c.svg",
                     "data/shipping-world-borders-v119.json"):
            self.assertIn(path,m.PATHS)
            self.assertTrue((ROOT/path).is_file(),path)
        self.assertEqual(len(m.PATHS),len(set(m.PATHS)))
    def test_v121_pulse_code_and_1_50m_geography_are_deployment_verified(self):
        for path in ("shipping.html","shipping-market-pulse-v121.mjs",
                     "shipping-market-pulse-v121.css","scripts/maritime-pulse-v121.mjs",
                     "brand/world-land-ne50-v119c.svg",
                     "brand/world-borders-ne50-v119c.svg"):
            self.assertIn(path,m.PATHS)
            self.assertTrue((ROOT/path).is_file(),path)
    def test_requires_exact_production_origin(self):
        with self.assertRaises(ValueError):
            m.check(base="https://example.invalid/",attempts=1,interval=0,fetch=lambda p,n:b"fake")
    def test_excluded_paths_fail_closed_even_when_public_files_match(self):
        with tempfile.TemporaryDirectory() as d:
            prior=m.ROOT
            try:
                m.ROOT=Path(d)
                for p in m.PATHS:
                    (m.ROOT/p).parent.mkdir(parents=True,exist_ok=True)
                    (m.ROOT/p).write_bytes(b"public")
                for code in (200,301,302,403,429,500,522,None):
                    with self.subTest(code=code),self.assertRaises(RuntimeError):
                        m.check(attempts=1,interval=0,fetch=lambda p,n:b"public",probe=lambda p,n:code)
                result=m.check(attempts=1,interval=0,fetch=lambda p,n:b"public",probe=lambda p,n:410)
                self.assertEqual({p for p,v in result.items() if v.get("excluded")},set(m.EXCLUDED_PATHS))
            finally:m.ROOT=prior
    def test_actual_http_probe_uses_get_without_reading_body(self):
        from urllib.error import HTTPError
        from io import BytesIO
        for code in (404,410,302,403):
            def opener(req,timeout):
                self.assertEqual(req.get_method(),"GET")
                self.assertEqual(req.full_url.split("?")[0],m.BASE+m.EXCLUDED_PATHS[0])
                raise HTTPError(req.full_url,code,"fixture",{},BytesIO(b"never log this"))
            self.assertEqual(m.exclusion_status(m.BASE,m.EXCLUDED_PATHS[0],1,opener=opener),code)
        self.assertIsNone(m.NoRedirect().redirect_request(None,None,302,None,None,"https://example.invalid"))
if __name__=="__main__":unittest.main()
