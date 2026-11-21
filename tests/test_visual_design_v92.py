"""V92 design source/regression gates. Browser appearance checked separately."""
from pathlib import Path
from unittest import TestCase
import re

ROOT=Path(__file__).resolve().parents[1]
PAGES=("terminal","stocks","news","shipping","commodities",
       "spreads","health","compare","calendar","shorts")
class V92DesignTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=(ROOT/"index.html").read_text(encoding="utf-8")
        cls.js=(ROOT/"v4.js").read_text(encoding="utf-8")
        cls.css=(ROOT/"overview-design-v92.css").read_text(encoding="utf-8")
        cls.category=(ROOT/"category-design-v92.css").read_text(encoding="utf-8")
    def test_approved_design_assets_and_load_order(self):
        self.assertIn('overview-design-v92.css?v=1',self.index)
        self.assertLess(self.index.index("overview-ux-v90.css?v=1"),
                        self.index.index("overview-design-v92.css?v=1"))
        self.assertIn("sw92-focus-grid",self.js)
        self.assertIn("sw92-focus-chart",self.js)
        self.assertIn("sw92-focus-summary",self.js)
        self.assertIn("sw92-quick-tools",self.js)
    def test_real_economic_history_promoted_to_first_fold(self):
        self.assertIn("const officialChart=overview.querySelector('.sw-overview-workbench')",self.js)
        self.assertIn("focus.append(officialChart,datedSummary)",self.js)
        self.assertIn("marketGrid.before(focus)",self.js)
        self.assertIn("if(officialChart)loadOfficialHistory()",self.js)
        self.assertIn("overviewResearch().catch",self.js)
        self.assertIn("if(economy.open)loadOfficialHistory()",self.js)
        self.assertNotIn("live prices from sample data",self.js)
    def test_hero_style_and_responsive_breakpoints(self):
        for name in (".sw92-focus-grid",".sw92-focus-chart",".sw92-focus-summary",
                     ".sw92-quick-tools",".sw-index-grid",".sw87-market-grid"):
            self.assertIn(name,self.css)
        self.assertIn("@media(max-width:900px)",self.css)
        self.assertIn("@media(max-width:600px)",self.css)
        self.assertIn("grid-template-columns:minmax(0,1fr)",self.css)
        self.assertEqual(self.css.count("{"),self.css.count("}"))
        self.assertNotIn("!important",self.css)
    def test_all_main_category_pages_load_themes_without_overriding_data(self):
        for page in PAGES:
            with self.subTest(page=page):
                html=(ROOT/(page+".html")).read_text(encoding="utf-8")
                self.assertIn('data-page="'+page+'"',html)
                self.assertIn('category-design-v92.css?v=1',html)
                self.assertLess(html.index("shell-v47.css"),html.index("category-design-v92.css"))
                self.assertIn('<main class="sw-content">',html)
                self.assertIn('class="sw-layout"',html)
                self.assertIn("sw-mobile-nav",html)
        self.assertEqual(self.category.count("{"),self.category.count("}"))
        self.assertNotIn("display:none",self.category)
        self.assertNotIn("!important",self.category)
        self.assertNotIn("@import",self.category)
    def test_specific_category_visual_intent(self):
        for page in ("stocks","terminal","news","shipping","commodities",
                     "spreads","compare","calendar","shorts","health"):
            self.assertIn('data-page='+page,self.category)
        self.assertIn("news-item-title",self.category)
        self.assertIn("marketCoverage",self.category)
        self.assertIn("sw49-workbench",self.category)
        self.assertIn("sw-page-head",self.category)
    def test_only_actual_links_no_internal_design_goals_in_public_ui(self):
        for href in ("terminal.html","stocks.html","compare.html","news.html","health.html"):
            self.assertIn('<a href="'+href+'">',self.js)
        for phrase in ("Target design level","Our design goals","Design palette",
                       "INTERNAL NOTES","Mockup prices"):
            self.assertNotIn(phrase,self.index)
            self.assertNotIn(phrase,self.js)
        self.assertNotIn("new Date().toLocaleString()",self.js)
    def test_existing_source_and_heatmap_behavior_preserved(self):
        for marker in ("function overviewMacroPoints","overviewMacroSeries","overviewMacroRange",
                       "overviewLensDot","workspaceHeatmap","workspaceHeatCount",
                       "latestBroadReportedSession","overviewEconomicCards","overviewDatasetCount"):
            self.assertIn(marker,self.js)
        self.assertEqual(self.index.count('id="main-content"'),1)
