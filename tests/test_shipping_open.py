"""Verify USDA ocean indices are real dated observations and never quoted as USD/tonne prices."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import shipping_open as s
class ShippingOpenTests(unittest.TestCase):
    def test_real_documented_usda_fields_only(self):
        rows=[{"date":"2026-11-11T00:00:00.000","gulf_vessel":"185.61","pacific_vessel":"187.65"},
              {"date":"2026-11-04T00:00:00.000","gulf_vessel":"190.06","pacific_vessel":"187.65"},
              {"date":"2026-11-07T00:00:00.000","gulf_vessel":"not available","pacific_vessel":"Infinity"},
              {"date":"broken","gulf_vessel":"200","pacific_vessel":"200"}]
        data=s.valid_rows(rows)
        self.assertEqual(data["usda:gulf-japan-index"][-1],{"date":"2026-11-11","value":185.61})
        self.assertEqual(len(data["usda:gulf-japan-index"]),2)
        self.assertEqual(len(data["usda:pnw-japan-index"]),2)
    def test_two_series_are_indices_not_rates(self):
        rows=[{"date":"2026-11-11T00:00:00.000","gulf_vessel":"185.61","pacific_vessel":"187.65"}]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/"data").mkdir()
            with mock.patch.object(s,"fetch_rows",return_value=rows):
                x=s.build(root)
            self.assertEqual(x["source"]["status"],"ok")
            self.assertEqual(len(x["series"]),2)
            self.assertTrue(all(z["isActualRate"] is False for z in x["series"]))
            self.assertTrue(all(z["unit"]=="index, 2017 = 100" for z in x["series"]))
            self.assertIn("NOT spot freight quotes",x["notice"])
            self.assertEqual(x["series"][0]["history"][-1]["date"],"2026-11-11")
    def test_failed_refresh_preserves_original_observed_at(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/"data").mkdir()
            old={"series":[{"key":"usda:gulf-japan-index","observedAt":"2026-11-11T00:00:00Z",
                "history":[{"date":"2026-11-11","value":185.61}]}],
                "source":{"lastSuccessAt":"2026-11-11T00:00:00Z"}}
            (root/s.OUT).write_text(json.dumps(old))
            with mock.patch.object(s,"fetch_rows",side_effect=TimeoutError):
                x=s.build(root)
            self.assertEqual(x["source"]["status"],"error")
            self.assertEqual(x["series"][0]["observedAt"],"2026-11-11T00:00:00Z")
    def test_avoid_vendor_quotes_and_unsupported_rate_units(self):
        self.assertEqual(len(s.RELATED),5)
        self.assertTrue(all(row.get("status") in ("link_only","license_required") for row in s.RELATED))
        self.assertFalse(any("USD/tonne"==x["field"] for x in s.ROUTES.values()))
if __name__=="__main__":unittest.main()
