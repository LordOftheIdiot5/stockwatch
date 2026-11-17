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
if __name__=="__main__":
    unittest.main()
