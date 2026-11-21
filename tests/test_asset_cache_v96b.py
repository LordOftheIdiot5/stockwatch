"""V96b browser cache release contract across primary Stockwatch workspaces."""
from pathlib import Path
from unittest import TestCase
ROOT=Path(__file__).resolve().parents[1]
PAGES=("index","stocks","company","calendar","compare","health","news",
       "commodities","intelligence","price-history","shipping","shorts",
       "spreads","terminal")
class AssetCacheV96bTests(TestCase):
    def test_critical_scripts_have_new_release_query_on_all_pages(self):
        for path in PAGES:
            with self.subTest(page=path):
                s=(ROOT/(path+".html")).read_text(encoding="utf-8")
                self.assertIn("release=v96b-20261121",s)
                self.assertIn("v4.js",s)
                if path in ("calendar","news","health","compare"):
                    self.assertIn("research.js",s)
    def test_release_verifier_covers_dynamic_application_assets(self):
        s=(ROOT/"scripts/verify_pages_release.py").read_text(encoding="utf-8")
        for target in ("calendar.html","company.html","index.html","v4.js",
                       "research.js","freshness-v96.css"):
            self.assertIn('"'+target+'"',s)
        self.assertIn("len(PATHS)",s)
