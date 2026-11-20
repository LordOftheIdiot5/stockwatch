import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class OverviewTests(unittest.TestCase):
    def test_single_pulse_and_scoped_css(self):
        html=(ROOT/"index.html").read_text()
        self.assertEqual(html.count('id="globalMarketPulse"'),1)
        self.assertIn('overview-v89j.css',html)
        self.assertIn('id="globalIndexData"',html)
        css=(ROOT/"overview-v89j.css").read_text()
        self.assertIn('body[data-page=index] .sw-content',css)
        self.assertIn('max-width:1000px',css)
    def test_preserve_repeated_render_and_map_controls(self):
        js=(ROOT/"v4.js").read_text()
        self.assertIn("if(globalPulse)globalPulse.remove()",js)
        self.assertIn("marketGrid.before(globalPulse)",js)
        self.assertIn("snapshot.append(heading,metrics)",js)
        self.assertIn("workspaceHeatExpand",js)
    def test_real_history_and_no_fabricated_value(self):
        js=(ROOT/"global-market-pulse.js").read_text()
        self.assertIn("chart(d.history,x)",js)
        self.assertIn("Last closing data unavailable",js)
        self.assertIn("TWSE source",js)
