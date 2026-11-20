"""V90 overview UX guardrails; static assertions, not a browser/contrast audit."""
import unittest
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
class OverviewUXV90Tests(unittest.TestCase):
    def setUp(self):
        self.html=(ROOT/"index.html").read_text(encoding="utf-8")
        self.css=(ROOT/"overview-ux-v90.css").read_text(encoding="utf-8")
    def test_overview_only_stylesheet_and_accessible_skip(self):
        self.assertIn('overview-v89j.css?v=1',self.html)
        self.assertIn('overview-ux-v90.css?v=1',self.html)
        self.assertLess(self.html.index("overview-v89j.css?v=1"),self.html.index("overview-ux-v90.css?v=1"))
        self.assertIn('href="#main-content"',self.html)
        self.assertEqual(self.html.count('id="main-content"'),1)
        self.assertIn('<main class="sw-content" id="main-content" tabindex="-1">',self.html)
        self.assertIn('.sw-skip-content-v90:focus',self.css)
    def test_no_more_centered_desktop_cap(self):
        self.assertIn('body[data-page="index"] .sw-content{',self.css)
        self.assertRegex(self.css,r'body\[data-page="index"\] \.sw-content\{[^}]*max-width:none;[^}]*margin-inline:0;')
        self.assertIn("width:100%",self.css)
        self.assertIn("@media(max-width:740px)",self.css)
        self.assertIn("@media(max-width:390px)",self.css)
        self.assertNotIn("position:absolute",self.css)
    def test_source_modules_not_hidden_by_css(self):
        for marker in ("#workspaceHeatmap",".sw-index-grid",".sw87-market-grid",".sw-overview-news",
                       ".sw-nav-label",".sw-link",".sw-index-spark"):
            self.assertIn(marker,self.css)
        self.assertNotIn("display:none",self.css)
        self.assertNotIn("visibility:hidden",self.css)
        self.assertNotIn("!important",self.css)
    def test_nav_and_market_source_integrity(self):
        for href in ("index.html","terminal.html","stocks.html","news.html",
                     "shipping.html","commodities.html","spreads.html","health.html"):
            self.assertIn(f'href="{href}"',self.html)
        self.assertIn('id="globalMarketPulse"',self.html)
        self.assertIn('id="globalIndexData"',self.html)
        self.assertIn('id="v4app"',self.html)
    def test_browser_capture_supports_extra_sizes_without_changing_default(self):
        script=(ROOT/"scripts/visual_audit.py").read_text(encoding="utf-8")
        for device in ("small-mobile","tablet","wide"):
            self.assertIn(f'"{device}"',script)
        self.assertIn('DEFAULT_VIEWPORTS = ("desktop", "mobile")',script)
        self.assertIn("contentRightGapPx",script)
        self.assertIn("contentUsableWidthRatio",script)
