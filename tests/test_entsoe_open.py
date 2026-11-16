import json
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
import urllib.error
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import entsoe_open as m

START=datetime(2026,11,15,tzinfo=timezone.utc)
END=START+timedelta(days=1)
PARAM={"documentType":"A65","processType":"A01","outBiddingZone_Domain":m.ZONES["NO1"]}
XML=b'''<GL_MarketDocument xmlns="urn:iec62325"><type>A65</type><process.processType>A01</process.processType><TimeSeries><outBiddingZone_Domain.mRID>10YNO-1--------2</outBiddingZone_Domain.mRID><quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name><curveType>A03</curveType><Period><timeInterval><start>2026-11-15T00:00Z</start><end>2026-11-16T00:00Z</end></timeInterval><resolution>PT15M</resolution><Point><position>1</position><quantity>100</quantity></Point><Point><position>3</position><quantity>200</quantity></Point></Period></TimeSeries></GL_MarketDocument>'''
class OpenEnergyTests(unittest.TestCase):
    def test_sparse_points_not_filled(self):
        out=m.parse(XML,PARAM,START,END)
        self.assertEqual(len(out),2)
        self.assertEqual(out[1]["startUtc"],"2026-11-15T00:30:00Z")
        self.assertEqual(out[1]["mw"],200)
    def test_wrong_license_scope_and_units_rejected(self):
        for raw in (XML.replace(b"A01</process",b"A16</process"),
                    XML.replace(b"10YNO-1--------2",b"10YNO-2--------T"),
                    XML.replace(b"MAW",b"MWH"),b"<!DOCTYPE foo>"+XML):
            with self.assertRaises(ValueError):m.parse(raw,PARAM,START,END)
    def test_flow_direction_checked(self):
        p={"documentType":"A11","out_Domain":m.ZONES["NO1"],"in_Domain":m.ZONES["SE3"]}
        raw=XML.replace(b"GL_MarketDocument",b"Publication_MarketDocument").replace(b"<type>A65</type>",b"<type>A11</type>").replace(b"outBiddingZone_Domain.mRID",b"out_Domain.mRID").replace(b"<quantity_Measure",b"<in_Domain.mRID>10Y1001A1001A46L</in_Domain.mRID><quantity_Measure",1)
        self.assertEqual(len(m.parse(raw,p,START,END)),2)
        with self.assertRaises(ValueError):m.parse(raw,{**p,"in_Domain":m.ZONES["SE1"]},START,END)
    def test_missing_token_never_calls(self):
        def fail(*a):raise AssertionError("network called")
        doc=m.collect("",END,fail)
        self.assertTrue(all(s["status"]=="awaiting_token" for s in doc["series"]))
    def test_limit_stops_without_leaking_token(self):
        calls=[]
        def rate(*a):
            calls.append(1)
            raise urllib.error.HTTPError("https://example.org/?token=PRIVATE",429,"PRIVATE",None,None)
        doc=m.collect("PRIVATE",END,rate)
        self.assertEqual(len(calls),1)
        self.assertNotIn("PRIVATE",json.dumps(doc))
        self.assertTrue(all(s["status"]=="skipped_provider_limit" for s in doc["series"][1:]))
    def test_only_licensed_requests(self):
        items=list(m.plan())
        self.assertEqual(len(items),21)
        self.assertEqual({p["documentType"] for _,p in items},{"A65","A11"})
        self.assertTrue(all(p.get("processType")=="A01" for _,p in items if p["documentType"]=="A65"))
