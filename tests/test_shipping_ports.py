"""Tests for attributed annual TEU activity, separate from licensed freight quotes."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import shipping_ports as ports


class ShippingPortsTests(unittest.TestCase):
    def rows(self):
        return [
            {"indicator": {"id": ports.INDICATOR}, "countryiso3code": code,
             "date": year, "value": val}
            for code in ("WLD", "CHN", "SGP", "USA", "NLD")
            for year, val in (("2023", "123456.5"), ("2024", "123999.7"))
        ]

    def test_real_indicators_countries_and_units_only(self):
        rows = self.rows() + [
            {"indicator": {"id": "NOT.TEU"}, "countryiso3code": "WLD",
             "date": "2025", "value": "999999"},
            {"indicator": {"id": ports.INDICATOR}, "countryiso3code": "XXX",
             "date": "2025", "value": "200"},
            {"indicator": {"id": ports.INDICATOR}, "countryiso3code": "WLD",
             "date": "2025", "value": "Infinity"},
            {"indicator": {"id": ports.INDICATOR}, "countryiso3code": "WLD",
             "date": "not-a-year", "value": "111"},
        ]
        parsed = ports.valid_rows(rows)
        self.assertEqual(len(parsed["WLD"]), 2)
        self.assertEqual(parsed["WLD"][-1], {"date": "2024-12-31", "value": 123999.7})
        self.assertFalse("XXX" in parsed)

    def test_build_tags_annual_activity_not_freight_rate_and_updates_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "data").mkdir()
            (root / "data/dataset-catalog.json").write_text(
                json.dumps({"datasets": [{"path": "data/news-latest.json"}]}))
            with mock.patch.object(ports, "fetch_rows", return_value=self.rows()):
                result = ports.build(root)
            self.assertEqual(result["source"]["status"], "ok")
            self.assertEqual(len(result["series"]), 5)
            self.assertTrue(all(s["unit"] == "TEU" and
                                s["isActualRate"] is False and
                                s["frequency"] == "annual"
                                for s in result["series"]))
            self.assertIn("NOT spot freight rates", result["notice"])
            catalog = json.loads((root / "data/dataset-catalog.json").read_text())
            self.assertEqual(len(catalog["datasets"]), 2)

    def test_failure_preserves_previous_observations_and_timestamps(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "data").mkdir()
            prior = {"source": {"lastSuccessAt": "2026-11-12T12:00:00Z"},
                     "series": [{"observedAt": "2026-11-12T12:00:00Z",
                                 "history": [{"date": "2024-12-31", "value": 9}]}]}
            (root / ports.OUT).write_text(json.dumps(prior))
            with mock.patch.object(ports, "fetch_rows", side_effect=TimeoutError):
                result = ports.build(root)
            self.assertEqual(result["source"]["status"], "error")
            self.assertEqual(result["source"]["lastSuccessAt"], "2026-11-12T12:00:00Z")
            self.assertEqual(result["series"], prior["series"])

    def test_partial_response_cannot_clear_existing_valid_coverage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "data").mkdir()
            with mock.patch.object(ports, "fetch_rows", return_value=self.rows()[:2]):
                result = ports.build(root)
            self.assertEqual(result["source"]["status"], "error")
            self.assertEqual(result["series"], [])


if __name__ == "__main__":
    unittest.main()
