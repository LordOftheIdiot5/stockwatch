"""V93 static heatmap UX and category-scope regression checks."""
from pathlib import Path
from unittest import TestCase

ROOT=Path(__file__).resolve().parents[1]
CATEGORIES=("shipping","commodities","news","spreads","health")

class HeatmapUXV93Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=(ROOT/"index.html").read_text(encoding="utf-8")
        cls.stocks=(ROOT/"stocks.html").read_text(encoding="utf-8")
        cls.js=(ROOT/"heatmap-experience-v93.js").read_text(encoding="utf-8")
        cls.css=(ROOT/"heatmap-experience-v93.css").read_text(encoding="utf-8")
        cls.category=(ROOT/"category-graphics-v93.css").read_text(encoding="utf-8")
    def test_heatmap_assets_load_after_original(self):
        for html in (self.index,self.stocks):
            self.assertIn("heatmap-experience-v93.css?v=1",html)
            self.assertIn("heatmap-experience-v93.js?v=1",html)
            self.assertLess(html.index("v4.js?v=89j8-display-rights"),
                            html.index("heatmap-experience-v93.js?v=1"))
            self.assertIn('<script src="heatmap-experience-v93.js?v=1" defer></script>',html)
    def test_existing_heatmap_source_only_no_new_feed(self):
        for expected in ("workspaceHeatmap","stkHeat",
                         'querySelectorAll("a.sw-heat-cell")',
                         'getAttribute("title")','getAttribute("href")',
                         'new MutationObserver','textContent='):
            self.assertIn(expected,self.js)
        for forbidden in ("fetch(","XMLHttpRequest","sendBeacon",
                          "localStorage.setItem","new WebSocket",
                          "document.write("):
            self.assertNotIn(forbidden,self.js)
    def test_accessibility_and_missing_data_not_hid(self):
        for expected in ("aria-pressed","aria-live","focusin","pointerover",
                         "No verified movement","Dated retained/older data",
                         "not a live price","visible tiles","sw93-heat-comfortable",
                         "sw93-heat-picker"):
            self.assertIn(expected,self.js)
        self.assertNotIn("preventDefault(",self.js)
        self.assertIn('new URL(href,base)',self.js)
    def test_css_scoped_and_mobile(self):
        for css in (self.css,self.category):
            self.assertEqual(css.count("{"),css.count("}"))
            self.assertNotIn("!important",css)
            self.assertNotIn("@import",css)
            self.assertNotIn("display:none",css)
        for mark in ("@media(max-width:600px)",
                     "@media(prefers-reduced-motion:reduce)",
                     ".sw93-heat-detail",".sw93-heat-balance"):
            self.assertIn(mark,self.css)
    def test_category_styling_retains_existing_pages(self):
        for page in CATEGORIES:
            with self.subTest(page=page):
                html=(ROOT/(page+".html")).read_text(encoding="utf-8")
                self.assertIn('category-graphics-v93.css?v=1',html)
                self.assertLess(html.index("category-design-v92.css?v=1"),
                                html.index("category-graphics-v93.css?v=1"))
                self.assertIn("data-page="+page,self.category)
        for marker in ("#usdaShippingIndices","#routeChart","#commodityTabs",
                       ".news-day-head","#marketCoverage"):
            self.assertIn(marker,self.category)
    def test_underlying_market_quality_functions_still_present(self):
        source=(ROOT/"v4.js").read_text(encoding="utf-8")
        for name in ("observationQuality","marketHeatData","coverageHeatRows",
                     "neutralMapDetail","compactScreenerHeatmap",
                     "coverageHeatmap","latestBroadReportedSession"):
            self.assertIn("function "+name+"(",source)
