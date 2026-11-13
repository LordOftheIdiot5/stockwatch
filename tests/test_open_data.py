"""Offline contract tests for official no-key providers (no network needed)."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"scripts"))
import open_data as o


class OpenDataTests(unittest.TestCase):
    def test_csv_parses_dated_numeric_observations_only(self):
        sample = (b"\xef\xbb\xbfFREQ,TIME_PERIOD,OBS_VALUE\n"
                  b"B,2026-11-10,9.1234\nB,2026-11-11,9.55\n"
                  b"B,2026-11-12,not-a-number\nB,bad,100\n")
        self.assertEqual(o.parse_csv_series(sample), [
            {"date":"2026-11-10","value":9.1234},
            {"date":"2026-11-11","value":9.55}])
        semicolon = b"TIME_PERIOD;OBS_VALUE\n2026-11-10;10.1\n"
        self.assertEqual(o.parse_csv_series(semicolon)[0]["value"], 10.1)

    def test_world_bank_keeps_real_annual_values_per_country(self):
        data = [{"page":1}, [
            {"country":{"id":"NO"},"date":"2025","value":2.4},
            {"country":{"id":"NO"},"date":"2024","value":1.2},
            {"country":{"id":"SE"},"date":"2025","value":None},
            {"country":{"id":"US"},"date":"2025","value":3.1},
            {"country":{"id":"ZZ"},"date":"2025","value":999}
        ]]
        x=o.parse_world_bank(data, "NY.GDP.MKTP.KD.ZG")
        self.assertEqual([r["value"] for r in x["NO"]],[1.2,2.4])
        self.assertNotIn("SE",x)
        self.assertNotIn("ZZ",x)

    def test_eurostat_dimension_index_and_2026_schema(self):
        data = {"id":["freq","unit","coicop18","geo","time"],
                "size":[1,1,1,1,2],
                "dimension":{
                    "freq":{"category":{"index":{"M":0}}},
                    "unit":{"category":{"index":{"RCH_A":0}}},
                    "coicop18":{"category":{"index":{"TOTAL":0}}},
                    "geo":{"category":{"index":{"NO":0}}},
                    "time":{"category":{"index":{"2026-08":0,"2026-09":1}}}
                },"value":{"0":2.1,"1":2.5}}
        values=o.parse_eurostat(data)
        self.assertEqual([v["value"] for v in values],[2.1,2.5])
        self.assertEqual(values[-1]["date"],"2026-09-01")
        self.assertEqual(o.parse_eurostat(data,"SE"),[])

    def test_issuer_name_matches_are_conservative(self):
        records=[{"navn":"Example Marine ASA","organisasjonsnummer":"123456789"}]
        self.assertEqual(o.exact_candidate("Example Marine",records,lambda r:r["navn"]), records[0])
        self.assertIsNone(o.exact_candidate("Example",records,lambda r:r["navn"]))
        self.assertIsNone(o.exact_candidate("Example Marine",records*2,lambda r:r["navn"]))

    def test_identity_check_rotates_without_verifying_ticker(self):
        watch={"tickers":[{"ticker":"ABC.OL","name":"Example ASA"},
                          {"ticker":"XYZ.ST","name":"Example Sweden"}]}
        prev={"identityCandidates":[]}
        with mock.patch.object(o,"gleif_candidate",return_value=None) as g, \
             mock.patch.object(o,"brreg_candidate",return_value=None) as b, \
             mock.patch.object(o.time,"sleep",return_value=None):
            candidate, lookups, attempted, errors = o.identity_candidates(prev, watch, limit=3)
            self.assertEqual(candidate,[])
            self.assertEqual(attempted,{"gleif":2,"brreg":1})
            self.assertEqual(len(lookups),3)
            self.assertTrue(all(x["result"]=="no_unique_match" for x in lookups))
            old={"identityCandidates":[],"identityLookups":lookups}
            _,_,later,_=o.identity_candidates(old,watch,limit=3)
            self.assertEqual(later,{"gleif":0,"brreg":0})
            self.assertEqual(g.call_count,2)
            self.assertEqual(b.call_count,1)

    def test_failed_source_keeps_old_values_and_reports_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/"data").mkdir()
            old={"series":[{"key":"fx:USD/NOK","provider":"norges_bank","value":9.23,
                            "period":"2026-11-11","observedAt":"2026-11-11T16:00:00Z"}]}
            (root/"data/open-data.json").write_text(json.dumps(old),encoding="utf8")
            with mock.patch.object(o,"fx_norges",side_effect=ConnectionError("network down")), \
                 mock.patch.object(o,"fx_ecb",return_value=None), \
                 mock.patch.object(o,"world_bank",return_value=[]), \
                 mock.patch.object(o,"eurostat",return_value=[]), \
                 mock.patch.object(o,"public_shorts",return_value={"trackedInRegister":0,"matchedByVerifiedIsin":[]}), \
                 mock.patch.object(o,"utcnow",return_value="2026-11-13T00:00:00Z"):
                result=o.build(root,mode="daily",now=datetime(2026,11,13,tzinfo=timezone.utc))
            self.assertEqual(result["series"][0]["value"],9.23)
            self.assertEqual(result["series"][0]["observedAt"],"2026-11-11T16:00:00Z")
            status={s["id"]:s for s in result["sources"]}
            self.assertEqual(status["norges_bank"]["status"],"error")
            self.assertEqual(status["gleif"]["status"],"not_checked")
            self.assertEqual(json.loads((root/"data/open-data.json").read_text())["mode"],"daily")

    def test_network_client_has_descriptive_user_agent_and_size_cap(self):
        class FakeResponse:
            def __init__(self,p): self.p=p
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n): return self.p[:n]
        with mock.patch.object(o.urllib.request,"urlopen",return_value=FakeResponse(b'{}')) as opener:
            self.assertEqual(o.fetch_json("https://example.org/api"),{})
            self.assertIn("StockwatchResearch",opener.call_args.args[0].get_header("User-agent"))
        with mock.patch.object(o.urllib.request,"urlopen",return_value=FakeResponse(b"abcdef")):
            with self.assertRaises(ValueError): o.get_bytes("https://example.org/api",max_bytes=3)


if __name__=="__main__":
    unittest.main()
