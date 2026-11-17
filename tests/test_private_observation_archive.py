import datetime as dt
import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/"scripts"))
import private_observation_archive as archive

STAMP="2026-11-17T20:07:26+00:00"
def row(**kwargs):
    return dict({"ticker":"WAWI.OL","name":"Wallenius Wilhelmsen","exchange":"Oslo","currency":"NOK","date":"2026-11-17","close":166.7,"priceStatus":"reported","priceObservedAt":STAMP,"spark":[10,20]},**kwargs)
class ArchiveTests(unittest.TestCase):
    def test_only_dated_reported_values(self):
        snapshot={"generated":STAMP,"companies":[row(),row(ticker="OLD",priceStatus="retained"),row(ticker="FUTURE",date="2026-11-18"),row(ticker="BAD",close=True),row(ticker="MISSING",date=None),row(ticker="OLD_STAMP",priceObservedAt="2026-11-16T20:00:00Z")]}
        out=archive.scanner_observations(snapshot)
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]["date"],"2026-11-17")
        self.assertEqual(out[0]["close"],166.7)
        self.assertNotIn("spark",out[0])
        self.assertFalse(out[0]["officialClose"])
        with self.assertRaises(ValueError):
            archive.scanner_observations({"generated":STAMP,"companies":[row(),row()]})
    def test_permission_gate_and_partition(self):
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp)
            (root/"data").mkdir()
            (root/"data/shipping-roro-traffic.json").write_text(json.dumps({"schemaVersion":1,"provider":"Eurostat","datasetCode":"mar_go_qmc","licenseUrl":"https://ec.europa.eu/eurostat/help/copyright-notice","series":[{"key":"example"}]}))
            now=dt.datetime(2026,11,18,tzinfo=dt.timezone.utc)
            with patch.object(archive,"immutable_put",return_value="created") as put:
                status=archive.collect(object(),{},root=root,now=now)
                self.assertEqual(status[-1]["storageStatus"],"permission_pending")
                self.assertEqual(put.call_count,1)
                (root/"data/signals.json").write_text(json.dumps({"generated":STAMP,"companies":[row()]}))
                status=archive.collect(object(),{"STOCKWATCH_SCANNER_RETENTION_APPROVED":"true"},root=root,now=now)
                self.assertEqual(status[-1]["day"],"2026-11-17")
                self.assertTrue(put.call_args.args[2].startswith("observations/scanner-observations/2026-11-17/"))
                self.assertFalse(status[-1]["publicPublication"])
    def test_eligible_series_only(self):
        eia={"key":"eia:RBRTE","provider":"eia","sourceUrl":"https://www.eia.gov/opendata/","license":"EIA attribution","unit":"USD/barrel","history":[{"date":"2026-11-17","value":80}]}
        denied={**eia,"key":"fred:UNKNOWN"}
        spoof={**eia,"sourceUrl":"https://www.eia.gov.example.com/"}
        out=archive.official_snapshot("official-energy-macro",{"generated":STAMP,"series":[eia,denied,spoof],"privateMetadata":"not archived"})
        self.assertEqual(out["series"],[eia])
        self.assertNotIn("privateMetadata",out)
        with self.assertRaises(ValueError):
            archive.official_snapshot("official-energy-macro",{"series":[denied]})
    def test_real_published_source_snapshots(self):
        for kind,filename in archive.OFFICIAL_FILES.items():
            with self.subTest(kind=kind):
                d=json.loads((archive.ROOT/"data"/filename).read_text(encoding="utf8"))
                result=archive.official_snapshot(kind,d)
                self.assertGreater(len(result["series"]),0)
                self.assertNotIn("identityCandidates",result)
                self.assertNotIn("publicShorts",result)
                self.assertNotIn("sources",result)
if __name__=="__main__":
    unittest.main()
