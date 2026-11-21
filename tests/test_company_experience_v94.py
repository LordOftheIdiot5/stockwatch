"""V94 company design source-level checks, not a rendered visual audit."""
from pathlib import Path
from unittest import TestCase

ROOT=Path(__file__).resolve().parents[1]
class V94CompanyUXTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/"company.html").read_text(encoding="utf-8")
        cls.js=(ROOT/"company-experience-v94.js").read_text(encoding="utf-8")
        cls.css=(ROOT/"company-experience-v94.css").read_text(encoding="utf-8")
        cls.v4=(ROOT/"v4.js").read_text(encoding="utf-8")
    def test_styles_and_enhancer_after_existing_market_components(self):
        self.assertIn('company-experience-v94.css?v=1',self.html)
        self.assertIn('company-experience-v94.js?v=1',self.html)
        self.assertLess(self.html.index('company-driver-map-v88.css'),
                        self.html.index('company-experience-v94.css'))
        self.assertLess(self.html.index('v4.js?v=89j8-display-rights'),
                        self.html.index('company-experience-v94.js?v=1'))
        self.assertIn('<main class="sw-content">',self.html)
    def test_no_duplicate_prices_or_new_data_calls(self):
        for forbidden in ("fetch(","XMLHttpRequest","localStorage.setItem(",
                          "sendBeacon(","innerHTML=","document.write(","new WebSocket"):
            self.assertNotIn(forbidden,self.js)
        self.assertIn('new MutationObserver(enhance)',self.js)
        self.assertIn('chart.insertAdjacentElement("afterend",map)',self.js)
    def test_company_price_history_and_source_attribution_preserved(self):
        for marker in ('id="companyHistorySource"','id="individualChart"',
                       "StockwatchNativeChart.mount","sourceUrl","licenseReference",
                       "publicDisplayPermitted","No licensed dated prices",
                       "Price observation "):
            self.assertIn(marker,self.v4)
        self.assertIn("role","".join(("role","")))  # documented source state
        self.assertIn('history.setAttribute("aria-live","polite")',self.js)
        self.assertIn('actualChart.setAttribute("role","region")',self.js)
    def test_accessible_section_navigation(self):
        for marker in ('"navigation"','"aria-controls"','"aria-current"',
                       '"ArrowRight"','"ArrowLeft"','"Home"','"End"',
                       'event.preventDefault()','"sw94-current"'):
            self.assertIn(marker,self.js)
        self.assertNotIn("Target design level",self.html)
        self.assertNotIn("Target design level",self.js)
    def test_scoped_company_responsive_chart_styles(self):
        self.assertEqual(self.css.count("{"),self.css.count("}"))
        for marker in ("body[data-page=company]","#individualChart",".sw50-coverage",
                       ".sw-company-banner",".sw-company-tabs",".sw94-research-shortcuts",
                       "@media(max-width:390px)","@media(max-width:720px)",
                       "@media(prefers-reduced-motion:reduce)"):
            self.assertIn(marker,self.css)
        self.assertNotIn("!important",self.css)
        self.assertNotIn("@import",self.css)
        self.assertNotIn("display:none",self.css)
    def test_reference_only_research_keeps_distinct_design(self):
        self.assertIn("sw94-reference-profile",self.js)
        self.assertIn(".sw94-reference-profile .sw-identity-grid",self.css)
        self.assertIn("FIGI candidates remain unverified.",self.v4)
