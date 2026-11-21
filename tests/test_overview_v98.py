"""V98 approved design parity contracts without simulated market data."""
from pathlib import Path
from unittest import TestCase
ROOT=Path(__file__).resolve().parents[1]
class V98ParityTests(TestCase):
 def test_chart_breadth_news_order_and_source_truth(self):
  js=(ROOT/"v4.js").read_text(encoding="utf8")
  html=(ROOT/"index.html").read_text(encoding="utf8")
  css=(ROOT/"overview-parity-v98.css").read_text(encoding="utf8")
  for marker in ("rail.append(breadth,filings)","primary.append(rail)","sw98-primary","sw98-market-secondary","panelHeader('Sector heatmap'","Source freshness","snapshot.append(heading,metrics)"):
   self.assertIn(marker,js)
  self.assertIn("['fx:EUR/NOK','fx:USD/NOK','eia:RBRTE'",js)
  self.assertIn("x.unit&&link(x.sourceUrl)&&overviewMacroPoints(x).length>=2",js)
  self.assertIn('viewBox="0 0 640 286"',js)
  self.assertIn("Official economic chart",js)
  self.assertIn("Verified market indices",html)
  self.assertIn("Taiwan sources connected",html)
  self.assertIn("overview-parity-v98.css",html)
  self.assertIn("release=v96b-20261121&v98=98b",html)
  self.assertIn(".sw98-intelligence-rail",css)
  self.assertIn("placeIndices()",js)
  self.assertIn("officialChart.after(globalPulse)",js)
  self.assertIn(".sw96-source-status",css)
  self.assertNotIn("Target design level",html)
