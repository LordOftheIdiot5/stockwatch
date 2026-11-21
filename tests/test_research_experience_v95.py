"""V95 research navigation and source-safe category design contracts."""
from pathlib import Path
from unittest import TestCase

ROOT=Path(__file__).resolve().parents[1]
class V95ResearchUXTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=(ROOT/"directory.html").read_text(encoding="utf-8")
        cls.research=(ROOT/"research.html").read_text(encoding="utf-8")
        cls.intelligence=(ROOT/"intelligence.html").read_text(encoding="utf-8")
        cls.css=(ROOT/"reference-design-v95.css").read_text(encoding="utf-8")
        cls.js=(ROOT/"intelligence-experience-v95.js").read_text(encoding="utf-8")
    def test_unique_skip_landmark_and_page_identity(self):
        for page,html in (("directory",self.directory),
                          ("research",self.research),
                          ("intelligence",self.intelligence)):
            with self.subTest(page=page):
                self.assertIn('data-page="'+page+'"',html)
                self.assertEqual(html.count('id="main-content"'),1)
                self.assertIn('href="#main-content"',html)
                self.assertIn('reference-design-v95.css?v=1',html)
                self.assertIn('rel="canonical"',html)
                self.assertIn("sw95-skip",html)
    def test_directory_truthful_listing_search_and_pagination(self):
        for marker in ('id="query"','id="venue"','id="directoryRows"',
                       'id="directoryStatus"','id="records"','id="matches"',
                       'id="next"','id="prev"','role="search"','role="region"'):
            self.assertIn(marker,self.directory)
        self.assertIn("Prices are not connected in this directory.",self.directory)
        self.assertIn('href="research.html"',self.directory)
        self.assertIn('href="stocks.html"',self.directory)
    def test_research_jump_links_and_licence_guard(self):
        for anchor in ("history-evidence","identity-architecture",
                       "universe","openfigi-facilitator"):
            self.assertIn('id="'+anchor+'"',self.research)
            self.assertIn('href="#'+anchor+'"',self.research)
        for marker in ('id="historyMetrics"','id="targetRows"',
                       'id="targetDetail"','id="targetStatus"',
                       "reference records","source-linked"):
            self.assertIn(marker,self.research)
        self.assertNotIn("facilitator listing is not yet confirmed",self.research)
        self.assertIn("does not grant market-price display rights",self.research)
    def test_evidence_graph_annotates_without_adding_data_sources(self):
        self.assertIn('intelligence-experience-v95.js?v=1',self.intelligence)
        self.assertLess(self.intelligence.index('v4.js?v=84-network'),
                        self.intelligence.index('intelligence-experience-v95.js?v=1'))
        self.assertIn('id="v4app"',self.intelligence)
        self.assertIn('id="sharedEnergyContext"',self.intelligence)
        self.assertIn('class="sw95-intel-jump"',self.intelligence)
        for name in ("#commercialNetwork","#intelMap","#sharedEnergyContext"):
            self.assertIn('href="'+name+'"',self.intelligence)
        for part in ("intelMap","intelSearch","intelListing","sw95-graph-guide",
                     'setAttribute("aria-label"','new MutationObserver(enhance)'):
            self.assertIn(part,self.js)
        for forbidden in ("fetch(","XMLHttpRequest","sendBeacon","localStorage.setItem",
                          "document.write(","new WebSocket"):
            self.assertNotIn(forbidden,self.js)
    def test_distinct_and_responsive_styles_light_dark(self):
        self.assertEqual(self.css.count("{"),self.css.count("}"))
        for selector in ("data-page=directory","data-page=research","data-page=intelligence",
                         "data-theme=light","@media(max-width:390px)",
                         "@media(max-width:650px)",".sw95-reference-table",
                         ".sw95-graph-guide",".sw95-graph-kind",
                         ".sw95-brand-hero",".sw95-skip:focus"):
            self.assertIn(selector,self.css)
        self.assertNotIn("!important",self.css)
        self.assertNotIn("display:none",self.css)
        self.assertNotIn("@import",self.css)
    def test_no_internal_design_goal_panel(self):
        for content in (self.directory,self.research,self.intelligence,self.js):
            self.assertNotIn("Target design level",content)
            self.assertNotIn("Our design goals",content)
    def test_source_scripts_remain_connected(self):
        self.assertIn("brand/brand.js?v=87a-directory",self.directory)
        self.assertIn("brand/research-coverage.js?v=87f-navigation",self.research)
        self.assertIn("v4.js?v=84-network",self.intelligence)
        self.assertTrue((ROOT/"data/instrument-directory.json").exists())
        self.assertTrue((ROOT/"data/history-coverage.json").exists())
