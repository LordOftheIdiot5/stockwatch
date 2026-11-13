"""Contract tests for UNCTAD CC BY monthly liner index, no fabricated rates."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import shipping_unctad as s

class UNCTADShippingTests(unittest.TestCase):
    def sample(self):
        head = "Month,Economy Label,Index (average M2 2023 = 100),Growth rate year on year\n"
        return head + "".join(
            f"{period},{name},{val},1.0\n"
            for name in list(s.COUNTRIES)[:6]
            for period,val in (("2026M08","123.45"),("2026M09","130.72"))
        )

    def test_monthly_index_schema_and_no_derived_freight_rate(self):
        out=s.parse_csv(self.sample())
        self.assertEqual(out["China"][-1],{"date":"2026-09-01","value":130.72})
        self.assertEqual(len(out["Singapore"]),2)
        self.assertIn("not", s.__doc__.lower())

    def test_reject_missing_2023_index_header(self):
        with self.assertRaises(ValueError):
            s.parse_csv("Month,Economy,Freight Price\n2026M09,China,500\n")

    def test_publish_with_attribution_and_catalog(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"data").mkdir()
            (root/"data/dataset-catalog.json").write_text(json.dumps({"datasets":[]}))
            with mock.patch.object(s,"fetch_csv",return_value=self.sample()):
                result=s.build(root)
            self.assertEqual(result["source"]["status"],"ok")
            self.assertEqual(len(result["series"]),6)
            self.assertTrue(all(not x["isActualRate"] for x in result["series"]))
            self.assertTrue(all("CC BY 3.0 IGO" in x["license"] for x in result["series"]))

    def test_failure_preserves_old_data(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"data").mkdir()
            old={"source":{"lastSuccessAt":"2026-01-01T00:00:00Z"},
                 "series":[{"observedAt":"2026-01-01T00:00:00Z","history":[{"date":"2025-12-01","value":20}]}]}
            (root/s.OUT).write_text(json.dumps(old))
            with mock.patch.object(s,"fetch_csv",side_effect=TimeoutError):
                result=s.build(root)
            self.assertEqual(result["source"]["status"],"error")
            self.assertEqual(result["series"],old["series"])
            self.assertEqual(result["source"]["lastSuccessAt"],old["source"]["lastSuccessAt"])
if __name__ == "__main__":
    unittest.main()
