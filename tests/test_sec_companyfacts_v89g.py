import sys,unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sec_companyfacts import parse
class SECCompanyFacts(unittest.TestCase):
    def test_as_filed_period_and_units(self):
        row={"start":"2025-01-01","end":"2025-12-31","filed":"2026-02-01","accn":"0000000001-26-000001","form":"10-K","val":123}
        payload={"cik":1,"facts":{"us-gaap":{"Revenues":{"units":{"USD":[row,dict(row,accn="0000000001-26-000002",val=124),dict(row,filed="2027-01-01")],"EUR":[row]}}}}}
        records=parse("0000000001",payload,date(2026,11,19))
        self.assertEqual(len(records),2)
        self.assertEqual({r["value"] for r in records.values()},{123,124})
        self.assertTrue(all(r["unit"]=="USD" and r["start"]=="2025-01-01" for r in records.values()))
    def test_wrong_issuer_rejected(self):
        with self.assertRaisesRegex(ValueError,"cik_mismatch"):parse("0000000001",{"cik":2},date(2026,11,19))
