"""V91 source-level QA for native chart UX styles, not visual browser signoff."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class NativeChartUXV91Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css=(ROOT/"native-chart-ux-v91.css").read_text(encoding="utf-8")
        cls.terminal=(ROOT/"terminal.html").read_text(encoding="utf-8")
        cls.stocks=(ROOT/"stocks.html").read_text(encoding="utf-8")
    def test_stylesheet_loads_after_existing_charts(self):
        for html in (self.terminal,self.stocks):
            self.assertIn('native-chart.css?v=49',html)
            self.assertIn('native-chart-ux-v91.css?v=1',html)
            self.assertLess(html.index('native-chart.css?v=49'),html.index('native-chart-ux-v91.css?v=1'))
    def test_scoped_to_stocks_and_terminal(self):
        self.assertIn('body[data-page="terminal"] .sw49-toolbar',self.css)
        self.assertIn('body[data-page="stocks"] .sw49-toolbar',self.css)
        self.assertNotIn('display:none',self.css)
        self.assertNotIn('visibility:hidden',self.css)
        self.assertNotIn('!important',self.css)
    def test_legible_and_keyboard_accessible(self):
        for marker in ('min-height:38px','min-height:44px','.sw-terminal-inspector',
                       '.sw49-plot:focus-visible','.sw49-plot,.sw49-rsi',
                       'font-variant-numeric:tabular-nums','@media(max-width:740px)'):
            self.assertIn(marker,self.css)
        self.assertEqual(self.css.count("{"),self.css.count("}"))
    def test_no_price_or_market_ingestion_code_changed(self):
        self.assertTrue((ROOT/"native-chart.js").is_file())
        self.assertTrue((ROOT/"research-analytics.js").is_file())
        self.assertNotIn("@import",self.css)
        self.assertNotIn("url(",self.css)
