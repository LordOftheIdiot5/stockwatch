"""V105 daily price target, exchange coverage and recovery queue assertions."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from daily_price_coverage_v105 import build


def read(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class TestDailyPriceCoverageV105(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.coverage = read("data/listing-coverage-v1.json")
        cls.signals = read("data/signals.json")
        cls.health = read("data/source-health.json")
        cls.rights = read("scripts/source_entitlements_v102.json")

    def make(self, coverage=None, signals=None, health=None, rights=None):
        return build(coverage or self.coverage, signals or self.signals,
                     health or self.health, rights or self.rights)

    def test_all_500_listings_and_venue_totals_are_reconciled(self):
        score, queue = self.make()
        original = self.coverage["summary"]
        s = score["summary"]
        self.assertEqual(s["listings"], len(self.coverage["records"]))
        self.assertGreaterEqual(s["listings"], 500)
        self.assertEqual(s["datedPrice"], original["priced"])
        self.assertEqual(s["missingPrice"], original["missingPrice"])
        self.assertEqual(s["listings"], s["datedPrice"] + s["missingPrice"])
        self.assertEqual(sum(v["listings"] for v in score["byVenue"]), s["listings"])
        self.assertEqual(sum(v["missingPrice"] for v in score["byVenue"]), s["missingPrice"])
        self.assertEqual(len({v["venue"] for v in score["byVenue"]), len(score["byVenue"]))
        self.assertEqual(queue["totalListings"], s["listings"])
        self.assertEqual(queue["unpricedQueue"], s["missingPrice"])

    def test_heuristic_session_quality_is_not_certified_exchange_eod(self):
        score, queue = self.make()
        self.assertEqual(score["comparisonDate"], self.health["priceFreshness"]["comparisonDate"])
        self.assertEqual(score["summary"]["monitoredComparableHeuristic"],
                         self.health["priceFreshness"]["equities"]["comparable"])
        self.assertIsNone(score["summary"]["exchangeCertifiedDailyQuotes"])
        self.assertEqual(score["summary"]["rightsClearedCandidateProducts"] if
                         "rightsClearedCandidateProducts" in score["summary"] else
                         score["summary"]["registryAuthorizedCandidateProducts"], 0)
        self.assertIn("not proof of an exchange-certified", score["notice"])
        self.assertEqual(len(queue["candidates"]), len(self.coverage["records"]),
                         "Without licensed chart history every listing should stay in the review queue")

    def test_pair_price_only_never_becomes_a_qualified_daily_quote(self):
        score, queue = self.make()
        pair = [r for r in self.coverage["records"] if r["priceStatus"] == "pair_observation"]
        self.assertEqual(score["summary"]["pairOnly"], len(pair))
        records = {r["id"]: r for r in queue["candidates"]}
        for p in pair:
            self.assertIn("pair_reference_not_daily_series", records[p["id"]]["reasons"])
            self.assertTrue(records[p["id"]]["needsDailyVerification"])
            self.assertFalse(records[p["id"]]["needsSourcePrice"])

    def test_no_quote_is_requested_and_faster_scan_workflow_stays(self):
        scan = (ROOT / ".github/workflows/scan.yml").read_text(encoding="utf-8")
        heatmap = (ROOT / "v4.js").read_text(encoding="utf-8")
        self.assertIn('cron: "5 6-17 * * 1-5"', scan)
        self.assertIn('cron: "20 22 * * 1-5"', scan)
        self.assertIn("python scripts/scan.py", scan)
        self.assertIn("sw-ws-heatmap", heatmap)
        self.assertIn("sw-overview-chart", heatmap)
        self.assertIn("sw-heat-cell", heatmap)
        score, queue = self.make()
        self.assertIn("No automated vendor queries", queue["notice"])
        self.assertIn("do not alter the existing heatmap", score["notice"])

    def test_rejects_mismatched_snapshot_and_missing_security(self):
        bad = copy.deepcopy(self.coverage)
        bad["records"] = bad["records"][1:]
        with self.assertRaisesRegex(ValueError, "directory total"):
            self.make(coverage=bad)
        bad = copy.deepcopy(self.coverage)
        bad["records"].append(copy.deepcopy(bad["records"][0]))
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.make(coverage=bad)
        bad = copy.deepcopy(self.coverage)
        bad["generated"] = "2026-11-19T10:00:00Z"
        with self.assertRaisesRegex(ValueError, "exact same"):
            self.make(coverage=bad)
        bad_health = copy.deepcopy(self.health)
        bad_health["priceFreshness"]["comparisonDate"] = "2026-11-19"
        with self.assertRaisesRegex(ValueError, "differs"):
            self.make(health=bad_health)

    def test_rejects_future_and_fabricated_price_dates(self):
        i = next(i for i, r in enumerate(self.coverage["records"])
                 if r["priceStatus"] != "missing")
        bad = copy.deepcopy(self.coverage)
        bad["records"][i]["priceDate"] = "2999-12-31"
        with self.assertRaisesRegex(ValueError, "Future"):
            self.make(coverage=bad)
        bad = copy.deepcopy(self.coverage)
        bad["records"][i]["priceDate"] = None
        with self.assertRaisesRegex(ValueError, "contradiction"):
            self.make(coverage=bad)

    def test_source_heurstic_count_cannot_be_falsified(self):
        bad = copy.deepcopy(self.health)
        bad["priceFreshness"]["equities"]["comparable"] += 1
        with self.assertRaisesRegex(ValueError, "disagrees"):
            self.make(health=bad)
        bad = copy.deepcopy(self.rights)
        bad["sources"][0]["permissions"]["publicDisplay"] = True
        with self.assertRaises(ValueError):
            self.make(rights=bad)

    def test_recovery_queue_is_priority_sorted_and_no_unsupported_history(self):
        score, queue = self.make()
        rows = queue["candidates"]
        keys = [r["id"] for r in rows]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(score["summary"]["licensedHistory"], self.coverage["summary"]["licensedHistory"])
        self.assertEqual(score["summary"]["historyMissing"],
                         score["summary"]["listings"] - score["summary"]["licensedHistory"])
        if any(x["needsSourcePrice"] for x in rows):
            self.assertTrue(rows[0]["needsSourcePrice"])
        self.assertTrue(all(r["lastSavedDate"] is None for r in rows if r["needsSourcePrice"]))


if __name__ == "__main__":
    unittest.main()
