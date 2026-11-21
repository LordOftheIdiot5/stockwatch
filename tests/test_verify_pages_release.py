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
                for p in m.PATHS:(m.ROOT/p).write_bytes(("<html>"+p+"</html>").encode())
                attempts=[]
                def fetch(p,n):
                    attempts.append((p,n))
                    return b"stale" if n==1 else (m.ROOT/p).read_bytes()
                result=m.check(attempts=2,interval=0,fetch=fetch)
                self.assertTrue(all(x["match"] for x in result.values()))
                self.assertEqual(len(attempts),2*len(m.PATHS))
            finally:m.ROOT=prior
    def test_rejects_stale_content(self):
        with tempfile.TemporaryDirectory() as d:
            prior=m.ROOT
            try:
                m.ROOT=Path(d)
                for p in m.PATHS:(m.ROOT/p).write_text(p)
                with self.assertRaisesRegex(RuntimeError,"do not match"):
                    m.check(attempts=1,interval=0,fetch=lambda p,n:b"wrong")
            finally:m.ROOT=prior
    def test_v98_new_css_and_v97_source_health_assets_are_deploy_verified(self):
        for path in ("index.html","v4.js","overview-parity-v98.css","overview-target-v110.css","workspace-density-v110b.css","workspace-density-v110b.js","overview-structure-v110d.css","overview-structure-v110d.js","overview-geo-v110e.css","overview-geo-v110e.js","brand/world-land-ne110.svg",
                     "company-cockpit-v110c.css","company-cockpit-v110c.js",
                     "nasdaq-notices-v100.js","nasdaq-notices-v100.css","news.html",
                     "global-market-pulse.js","heatmap-experience-v93.js",
                     "overview-watchlist-v99.js","overview-watchlist-v99.css",
                     "health.html","price-evidence-v97.js","price-evidence-v97.css"):
            self.assertIn(path,m.PATHS)
        self.assertEqual(len(m.PATHS),len(set(m.PATHS)))
    def test_requires_exact_production_origin(self):
        with self.assertRaises(ValueError):
            m.check(base="https://example.invalid/",attempts=1,interval=0,fetch=lambda p,n:b"fake")
if __name__=="__main__":unittest.main()
