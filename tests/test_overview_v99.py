"""V99: personal watchlist must never synthesize holdings or quote freshness."""
from pathlib import Path
from unittest import TestCase
ROOT=Path(__file__).resolve().parents[1]
class V99WatchlistTests(TestCase):
 def test_uses_existing_saved_symbols_only(self):
  js=(ROOT/"v4.js").read_text(encoding="utf8")
  module=(ROOT/"overview-watchlist-v99.js").read_text(encoding="utf8")
  html=(ROOT/"index.html").read_text(encoding="utf8")
  css=(ROOT/"overview-watchlist-v99.css").read_text(encoding="utf8")
  for expected in ("stockwatch-terminal-v31","stockwatch-v4-favorites",
                   "No saved companies yet","Last saved","Price unavailable",
                   "No quantity or market value is assumed"):
   self.assertIn(expected,module)
  self.assertIn("StockwatchOverviewWatchlist?.mount",js)
  self.assertIn("overview-watchlist-v99.js",html)
  self.assertIn("overview-watchlist-v99.css",html)
  self.assertIn(".sw99-watch-pair",css)
  self.assertNotIn("Demo portfolio",module)
 def test_existing_source_truth_survives(self):
  js=(ROOT/"v4.js").read_text(encoding="utf8")
  self.assertIn("state.health?.priceFreshness",js)
  self.assertIn("Source freshness",js)
  self.assertIn("stockwatch-v4-favorites",js)
