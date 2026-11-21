"""V110: persist approved design and never invent values to resemble mockups."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class V110Tests(unittest.TestCase):
 def test_reference_spec_on_main(self):
  original=(ROOT/'docs/APPROVED-STOCKWATCH-DESIGN-TARGET-V1.md').read_text()
  roadmap=(ROOT/'ROADMAP.md').read_text()
  self.assertIn('df85998bd202dd9e4b3832a85edfaaf9fde78a417af4dcc3c7ced9e076be7b00',original)
  self.assertIn('V110a approved Overview visual recovery',roadmap)
  self.assertIn('NOT part of the public website',original)
 def test_real_heatmap_filters_are_available(self):
  js=(ROOT/'v4.js').read_text()
  self.assertIn('<option value="observed" selected>Dated changes only</option>',js)
  self.assertIn('Include dated prices / A/B references',js)
  self.assertIn('Without comparable changes',js)
  self.assertIn('sw110-heat-companion',js)
  self.assertIn('displayUniverse.filter(displayObservation)',js)
  self.assertIn('marketHeatData(displayUniverse)',js)
 def test_protect_all_existing_market_sources(self):
  html=(ROOT/'index.html').read_text()
  js=(ROOT/'v4.js').read_text()
  for text in ('global-market-pulse.js','heatmap-experience-v93.js',
               'overview-watchlist-v99.js','overview-target-v110.css'):
   self.assertIn(text,html)
  for text in ("overviewResearch().catch", "state.health?.priceFreshness",
               "StockwatchOverviewWatchlist?.mount", "overviewMacro",
               "renderOverviewEconomicCards"):
   self.assertIn(text,js)
if __name__=='__main__':unittest.main()
