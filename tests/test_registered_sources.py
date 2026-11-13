"""Offline tests of optional OpenFIGI and ENTSO-E connectors."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import registered_sources as m


class RegisteredSourceTests(unittest.TestCase):
    def test_jobs_filter_to_known_exchange_mic(self):
        d={"entities":[
            {"ticker":"ALPER.PA","isin":"FR0000061459"},
            {"ticker":"WWI.OL","isin":None},
            {"ticker":"UNKNOWN.XX","isin":None},
            {"ticker":"not a symbol.OL","isin":None}]}
        j=m.figi_jobs(d)
        self.assertEqual(len(j),2)
        self.assertEqual(j[0][1],{"idType":"ID_ISIN","idValue":"FR0000061459","micCode":"XPAR"})
        self.assertEqual(j[1][1],{"idType":"TICKER","idValue":"WWI","micCode":"XOSL"})

    def test_results_stay_unverified_and_ambiguous_rejected(self):
        jobs=[("WWI.OL",{"idType":"TICKER","idValue":"WWI","micCode":"XOSL"})]
        d=[{"data":[{"ticker":"WWI","marketSector":"Equity","figi":"BBG000BLNNH6",
                      "name":"WILH WILHELMSEN ASA"}]}]
        candidates,amb=m.parse_figi(d,jobs)
        self.assertEqual(amb,0)
        self.assertEqual(candidates[0]["verified"],False)
        self.assertEqual(candidates[0]["ticker"],"WWI.OL")
        mixed,amb=m.parse_figi([{"data":d[0]["data"]*2}],jobs)
        self.assertEqual(mixed,[])
        self.assertEqual(amb,1)
        with self.assertRaises(ValueError):m.parse_figi([],jobs)

    def test_credentials_are_only_request_headers_not_output(self):
        d={"entities":[{"ticker":"WWI.OL","isin":None}]}
        fake=[{"data":[{"ticker":"WWI","marketSector":"Equity","figi":"BBG000BLNNH6"}]}]
        with mock.patch.object(m,"_read",return_value=json.dumps(fake).encode()) as read:
            x=m.openfigi(d,"PRIVATE-TEST-KEY")
            req=read.call_args.args[0]
            self.assertEqual(req.get_header("X-openfigi-apikey"),"PRIVATE-TEST-KEY")
            self.assertNotIn("PRIVATE-TEST-KEY",json.dumps(x))
            self.assertEqual(x["count"],1)

    def test_entsoe_xml_probe_never_exposes_rates(self):
        xml=b'''<Publication_MarketDocument xmlns="urn:iec62325"><TimeSeries><Period>
          <Point><position>1</position><price.amount>34.21</price.amount></Point>
          <Point><position>2</position><price.amount>-10</price.amount></Point>
          </Period></TimeSeries></Publication_MarketDocument>'''
        self.assertEqual(m.inspect_entsoe_xml(xml),2)
        with self.assertRaises(ValueError):m.inspect_entsoe_xml(b"<Acknowledgement_MarketDocument/>")
        with mock.patch.object(m,"_read",return_value=xml) as read:
            x=m.entsoe_probe("PRIVATE-ENTSOE-TOKEN")
            req=read.call_args.args[0]
            self.assertIn("PRIVATE-ENTSOE-TOKEN",req.full_url)
            self.assertNotIn("PRIVATE-ENTSOE-TOKEN",json.dumps(x))
            self.assertFalse(x["dataStored"])
            self.assertFalse(x["publicDisplay"])
            self.assertNotIn("34.21",json.dumps(x))

    def test_entsoe_http_status_is_saved_without_token_or_secret_url(self):
        import urllib.error
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/"data").mkdir()
            (root/"data/issuer-identities.json").write_text('{"entities":[]}')
            exposed_url="https://web-api.tp.entsoe.eu/api?securityToken=PRIVATE-TEST-TOKEN"
            http=urllib.error.HTTPError(exposed_url,403,"Forbidden",None,None)
            with mock.patch.dict(os.environ,{"STOCKWATCH_ENTSOE_TOKEN":"PRIVATE-TEST-TOKEN"},clear=True), \
                 mock.patch.object(m,"entsoe_probe",side_effect=http):
                result=m.build(root)
            entsoe=result["sources"]["entsoe"]
            self.assertEqual(entsoe["httpStatus"],403)
            self.assertEqual(entsoe["diagnostic"],"token_not_authorized")
            serialized=json.dumps(result)
            self.assertNotIn("PRIVATE-TEST-TOKEN",serialized)
            self.assertNotIn("securityToken",serialized)

    def test_missing_keys_are_reported_without_exposing_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/"data").mkdir()
            (root/"data/issuer-identities.json").write_text('{"entities":[]}')
            with mock.patch.dict(os.environ,{},clear=True):
                result=m.build(root)
            self.assertEqual(result["sources"]["openfigi"]["status"],"awaiting_key")
            self.assertEqual(result["sources"]["entsoe"]["status"],"awaiting_token")
            self.assertEqual(result["figiCandidates"],[])
            self.assertTrue((root/"data/registered-source-status.json").exists())
