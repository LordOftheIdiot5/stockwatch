"""V104a daily licensed close ledger: source, session, idempotency and no-publication gates."""
import copy
import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from eod_close_ledger_v104 import ingest, chart_rows, reviewed_map, private_path

NOW = datetime(2026, 11, 21, 10, tzinfo=timezone.utc)
SOURCE = "unit_test_licensed_eod"
PRODUCT = "Synthetic EOD close testing only — NOT A REAL DATA GRANT"


def registry(display=False, retention=True, collection=True):
    flags = {"productionCollection": collection, "privateRetention": retention,
             "publicDisplay": display, "commercialExport": False}
    approved = [k for k, v in flags.items() if v]
    return {"schemaVersion": 1, "sources": [{
        "id": SOURCE, "provider": "Synthetic test exchange", "product": PRODUCT,
        "venues": ["NASDAQ US"], "observationKind": "primary_venue_eod_candidate",
        "sourceUrl": "https://example.org/synthetic-source",
        "policyUrl": "https://example.org/synthetic-policy",
        "policyFinding": "Unit test only", "reviewStatus": "synthetic_unit_test",
        "reviewedAt": "2026-11-21",
        "identity": {"isinMapped": True, "micMapped": True,
                     "currencyVerified": True, "sessionCloseVerified": True},
        "permissions": flags,
        "authorization": ({
            "sourceId": SOURCE, "product": PRODUCT, "scope": "SYNTHETIC TESTS ONLY",
            "evidenceRef": "SYNTHETIC-NOT-A-LICENSE", "reviewer": "unit test",
            "reviewedOn": "2026-11-21", "capabilities": approved
        } if approved else None)
    }]}


def mappings():
    return {"schemaVersion": 1, "mappings": [{
        "listingId": "AAPL", "isin": "US0378331005", "mic": "XNAS", "currency": "USD",
        "evidenceUrl": "https://example.org/synthetic-identity",
        "reviewed": True
    }]}


def bar(day="2026-11-20", close="280.22"):
    return {
        "sourceId": SOURCE, "listingId": "AAPL",
        "isin": "US0378331005", "mic": "XNAS", "currency": "USD",
        "sessionDate": day, "close": close, "volume": 1520000,
        "quoteKind": "primary_official_close", "sessionVerified": True,
        "publishedAt": day + "T22:35:00Z",
        "sourceUrl": "https://example.org/synthetic-bars",
        "sessionEvidenceUrl": "https://example.org/synthetic-calendar"
    }


class TestV104DailyClose(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.db = Path(self.folder.name) / "private.sqlite"

    def tearDown(self):
        self.folder.cleanup()

    def collect(self, rows=None, rights=None, maps=None):
        return ingest(self.db, SOURCE, rows or [bar()], maps or mappings(),
                      rights or registry(), {"AAPL"}, now=NOW)

    def test_default_real_registry_denies_all_new_eod_sources(self):
        original = json.loads((ROOT / "scripts/source_entitlements_v102.json").read_text())
        for x in original["sources"]:
            self.assertFalse(any(x["permissions"].values()), x["id"])
        with self.assertRaises(PermissionError):
            ingest(self.db, "nasdaq_nordic_eod", [bar()], mappings(), original, {"AAPL"}, NOW)
        self.assertFalse(self.db.exists())

    def test_one_close_per_session_is_enough_to_store_not_fake_chart(self):
        r = self.collect()
        self.assertEqual(r["records"], 1)
        self.assertFalse(r["publicDisplayActivated"])
        with self.assertRaises(PermissionError):
            chart_rows(self.db, SOURCE, "AAPL", registry())
        self.assertEqual(chart_rows(self.db, SOURCE, "AAPL", registry(display=True))["status"], "not_enough_history")

    def test_second_actual_day_makes_two_point_chart_when_public_display_approved(self):
        self.collect([bar("2026-11-19", "275.43")])
        self.collect([bar("2026-11-20", "280.22")])
        r = chart_rows(self.db, SOURCE, "AAPL", registry(display=True))
        self.assertEqual(r["status"], "ok")
        self.assertEqual([x["date"] for x in r["bars"]], ["2026-11-19", "2026-11-20"])
        self.assertEqual([x["close"] for x in r["bars"]], ["275.43", "280.22"])
        self.assertFalse(any("live" in x for x in r["bars"]))
        self.assertIn("not live quotes", r["notice"])

    def test_repeat_day_is_idempotent_but_correction_requires_review(self):
        self.collect()
        first = self.collect()
        self.assertEqual(first["records"], 1)
        with self.assertRaisesRegex(ValueError, "correction"):
            self.collect([bar(close="281.33")])
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("select count(*) from eod_daily_close").fetchone()[0], 1)

    def test_one_bad_row_rolls_back_whole_batch(self):
        self.collect([bar("2026-11-19")])
        with self.assertRaises(ValueError):
            self.collect([bar("2026-11-20"), bar("2026-11-19", "282")])
        with sqlite3.connect(self.db) as conn:
            self.assertEqual(conn.execute("select count(*) from eod_daily_close").fetchone()[0], 1)

    def test_wrong_venue_currency_security_future_and_unverified_rejected(self):
        variants = [
            ("mic", "XOSL"), ("isin", "US1234567890"),
            ("currency", "EUR"), ("sessionVerified", False),
            ("sessionDate", "2026-11-23"), ("close", "0"),
            ("close", "NaN"), ("publishedAt", "2026-11-22T20:00:00Z"),
            ("quoteKind", "unknown"),
            ("sourceUrl", "http://localhost/price")
        ]
        for k, v in variants:
            wrong = bar()
            wrong[k] = v
            with self.subTest(field=k, value=v), self.assertRaises((ValueError, PermissionError)):
                self.collect([wrong])
        self.assertFalse(self.db.exists())

    def test_entitlement_collection_retention_and_identity_all_required(self):
        for right in (registry(collection=False), registry(retention=False)):
            with self.assertRaises(PermissionError):
                self.collect(rights=right)
        wrong = registry()
        wrong["sources"][0]["identity"]["micMapped"] = False
        with self.assertRaises(PermissionError):
            self.collect(rights=wrong)
        self.assertFalse(self.db.exists())

    def test_mapping_and_batched_conflicts_denied(self):
        bad = mappings()
        bad["mappings"][0]["reviewed"] = False
        with self.assertRaises(ValueError):
            self.collect(maps=bad)
        with self.assertRaises(ValueError):
            reviewed_map({"schemaVersion": 1, "mappings": mappings()["mappings"] * 2})
        with self.assertRaisesRegex(ValueError, "Conflicting duplicate"):
            self.collect([bar(), bar(close="290")])
        with self.assertRaisesRegex(ValueError, "outside"):
            self.collect(maps={"schemaVersion": 1, "mappings": [dict(mappings()["mappings"][0], mic="XOSL")]},
                         rows=[dict(bar(), mic="XOSL")])

    def test_private_database_location_is_not_public_git_data(self):
        with self.assertRaises(ValueError):
            private_path(ROOT / "data" / "secret.sqlite")
        with self.assertRaises(ValueError):
            self.collect(rows=[dict(bar(), sessionEvidenceUrl="http://example.org/")])
        self.assertFalse(self.db.exists())

    def test_alternative_venue_is_not_official_primary_close(self):
        rights = registry()
        rights["sources"][0]["observationKind"] = "alternative_venue_eod_candidate"
        with self.assertRaisesRegex(ValueError, "alternative-venue"):
            self.collect(rights=rights)


if __name__ == "__main__":
    unittest.main()
