"""V104b: existing charts, heatmaps, faster quotes survive additive licensed EOD."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from presentation_price_layers_v104b import compose_display_layers


def existing(day="2026-11-20", price=103.5):
    return {"ticker": "SALM.OL", "close": price, "date": day, "currency": "NOK",
            "source": "existing_market_scanner", "priceStatus": "reported",
            "changePct": 1.2, "volume": 1000, "spark": [99, 103.5]}


def eod(last="2026-11-20"):
    return {
        "status": "ok", "listingId": "SALM.OL", "source": "Synthetic provider",
        "product": "Synthetic daily close only, never publish",
        "bars": [
            {"date": "2026-11-19", "close": "100.25", "mic": "XOSL",
             "currency": "NOK", "kind": "primary_official_close",
             "sourceUrl": "https://example.org/source", "publishedAt": "2026-11-19T18:00:00Z"},
            {"date": last, "close": "101.00", "mic": "XOSL",
             "currency": "NOK", "kind": "primary_official_close",
             "sourceUrl": "https://example.org/source", "publishedAt": last + "T18:00:00Z"}
        ],
    }


class PricePresentationV104bTests(unittest.TestCase):
    def test_same_day_faster_source_stays_primary_and_is_unmodified(self):
        fast = existing()
        original = copy.deepcopy(fast)
        r = compose_display_layers("SALM.OL", fast, eod(), True)
        self.assertEqual(r["selectedLayer"], "existing_observation")
        self.assertEqual(r["displayQuote"], fast)
        self.assertEqual(fast, original)
        self.assertEqual(r["existingObservation"]["changePct"], 1.2)
        self.assertEqual(r["existingObservation"]["spark"], [99, 103.5])
        self.assertEqual(len(r["licensedDailyHistory"]), 2)
        self.assertEqual(r["heatmapSignalSource"], "existing_scanner_only")

    def test_older_eod_never_downgrades_current_existing_feed(self):
        r = compose_display_layers("SALM.OL", existing(), eod("2026-11-19"), True)
        # Duplicate date makes EOD history invalid: existing still wins.
        self.assertEqual(r["selectedLayer"], "existing_observation")
        self.assertEqual(r["displayQuote"]["date"], "2026-11-20")
        self.assertEqual(r["displayQuote"]["close"], 103.5)

    def test_newer_approved_eod_fills_a_gap_but_preserves_fast_source(self):
        fast = existing("2026-11-19")
        r = compose_display_layers("SALM.OL", fast, eod(), True)
        self.assertEqual(r["selectedLayer"], "licensed_eod_fallback")
        self.assertEqual(r["displayQuote"]["date"], "2026-11-20")
        self.assertEqual(r["displayQuote"]["frequency"], "daily")
        self.assertEqual(r["existingObservation"], fast)
        self.assertNotIn("changePct", r["displayQuote"])

    def test_without_public_rights_no_eod_history_or_daily_fallback(self):
        r = compose_display_layers("SALM.OL", existing("2026-11-19"), eod(), False)
        self.assertEqual(r["selectedLayer"], "existing_observation")
        self.assertEqual(r["licensedDailyHistory"], [])
        self.assertEqual(r["displayQuote"]["date"], "2026-11-19")
        r = compose_display_layers("SALM.OL", None, eod(), False)
        self.assertEqual(r["selectedLayer"], "unavailable")
        self.assertIsNone(r["displayQuote"])

    def test_missing_faster_feed_can_gain_separately_approved_eod(self):
        r = compose_display_layers("SALM.OL", None, eod(), True)
        self.assertEqual(r["selectedLayer"], "licensed_eod_fallback")
        self.assertEqual(r["displayQuote"]["close"], 101.0)
        self.assertIsNone(r["existingObservation"])
        self.assertEqual(r["displayQuote"]["mic"], "XOSL")

    def test_price_currency_source_or_identity_mismatch_fails_closed(self):
        foreign = copy.deepcopy(eod())
        foreign["listingId"] = "OTHER"
        r = compose_display_layers("SALM.OL", existing(), foreign, True)
        self.assertEqual(r["licensedDailyHistory"], [])
        self.assertEqual(r["selectedLayer"], "existing_observation")
        mismatched_currency = eod()
        mismatched_currency["bars"] = [
            dict(x, currency="SEK") for x in mismatched_currency["bars"]
        ]
        r = compose_display_layers("SALM.OL", existing(), mismatched_currency, True)
        self.assertEqual(r["licensedDailyHistory"], [])
        self.assertEqual(r["displayQuote"]["close"], 103.5)

    def test_no_fake_synthetic_gaps_and_ambiguous_dates_are_rejected(self):
        series = eod()
        series["bars"][0]["date"] = "2026-11-18"
        r = compose_display_layers("SALM.OL", None, series, True)
        self.assertEqual([x["date"] for x in r["licensedDailyHistory"]],
                         ["2026-11-18", "2026-11-20"])
        self.assertEqual(len(r["licensedDailyHistory"]), 2)
        duplicated = eod()
        duplicated["bars"][0]["date"] = "2026-11-20"
        self.assertEqual(compose_display_layers("SALM.OL", None, duplicated, True)["licensedDailyHistory"], [])
        invalid = eod()
        invalid["bars"][0]["close"] = "NaN"
        self.assertEqual(compose_display_layers("SALM.OL", None, invalid, True)["selectedLayer"], "unavailable")

    def test_existing_visualization_elements_are_not_removed_by_eod_release(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        app = (ROOT / "v4.js").read_text(encoding="utf-8")
        heatmap = (ROOT / "heatmap-experience-v93.js").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "scan.yml").read_text(encoding="utf-8")
        for marker in ("heatmap-experience-v93.js", "global-market-pulse.js",
                       "overview-watchlist-v99.js", 'id="v4app"'):
            self.assertIn(marker, index)
        for marker in ("sw-ws-heatmap", "sw-overview-chart", "overviewMacroPlot",
                       "overviewMacroSeries", "StockwatchOverviewWatchlist",
                       "sw-heat-cell", "officialChart"):
            self.assertIn(marker, app)
        self.assertIn('const ROOTS=["workspaceHeatmap","stkHeat"]', heatmap)
        self.assertIn("data-strength", app)
        self.assertIn("python scripts/scan.py", workflow)
        self.assertIn("python scripts/build_research_data.py", workflow)
        self.assertNotIn("presentation_price_layers_v104b", workflow,
                         "EOD quote composition must not replace the frequent scanner.")


if __name__ == "__main__":
    unittest.main()
