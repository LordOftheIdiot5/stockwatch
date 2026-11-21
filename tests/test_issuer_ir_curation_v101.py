"""V101d issuer source-link triage: never confuse candidates with report files."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from issuer_ir_curation_v101 import curate, classify_link


class V101DCurationTests(unittest.TestCase):
    def setUp(self):
        self.registry=json.loads((ROOT/"scripts/issuer_ir_sources_v101.json").read_text())
        self.salm=next(x for x in self.registry["sources"] if x["ticker"]=="SALM.OL")

    def candidate(self,url,**kw):
        return {
            "ticker":"SALM.OL",
            "sourcePage":self.salm["landingPage"],
            "documentUrl":url,
            "linkText":"Annual Report 2025 Download",
            "kindCandidate":"annual_report","fiscalYearCandidate":2025,
            "quarterCandidate":None,
            "documentDownloaded":False,"privateRetentionApproved":False,
            **kw
        }

    def test_actual_report_files_and_landing_are_differentiated(self):
        rows=[
          self.candidate("https://www.salmar.no/files/2025-salmar-report.pdf"),
          self.candidate("https://www.salmar.no/files/2025-esef.zip",kindCandidate="esef"),
          self.candidate("https://ml-eu.globenewswire.com/Resource/Download/abc"),
          self.candidate("https://www.salmar.no/en/investor/financial-calendar/2025/",linkText="Calendar"),
          self.candidate("https://www.salmar.no/files/2025-salmar-report.pdf")
        ]
        r=curate({"schemaVersion":1,"generated":"2026-11-21T00:00:00Z","items":rows},self.registry)
        self.assertEqual(r["inputCandidateCount"],4)
        self.assertEqual(r["reviewQueueCount"],3)
        self.assertEqual(r["discardedCount"],1)
        self.assertEqual(r["byLinkType"],{"direct_file":2,"opaque_download":1,"other_page":1})
        self.assertTrue(all(not x["verifiedDocument"] and not x["documentStored"] for x in r["items"]))
        self.assertTrue(all(not x["privateRetentionApproved"] for x in r["items"]))

    def test_denies_cross_site_injected_and_fabricated_rights(self):
        bad=self.candidate("https://evil.example/annual-report-2025.pdf")
        with self.assertRaises(ValueError):
            curate({"schemaVersion":1,"items":[bad]},self.registry)
        bad=self.candidate("https://www.salmar.no/report-2025.pdf",privateRetentionApproved=True)
        with self.assertRaises(ValueError):
            curate({"schemaVersion":1,"items":[bad]},self.registry)
        bad=self.candidate("https://www.salmar.no/report-2025.pdf",documentDownloaded=True)
        with self.assertRaises(ValueError):
            curate({"schemaVersion":1,"items":[bad]},self.registry)
        bad=self.candidate("https://www.salmar.no/report-2025.pdf",sourcePage="https://evil.example/")
        with self.assertRaises(ValueError):
            curate({"schemaVersion":1,"items":[bad]},self.registry)

    def test_nonfiles_remain_outside_verified_review_queue(self):
        r=curate({"schemaVersion":1,"items":[self.candidate("https://www.salmar.no/en/news/some-results-2025")]},self.registry)
        self.assertEqual(r["reviewQueueCount"],0)
        self.assertEqual(r["discardedCount"],1)
        self.assertFalse(r["items"])
        self.assertIn("not verified reports",r["notice"])

    def test_classify_download_endpoints_without_claiming_format(self):
        typ,fmt=classify_link("https://ml-eu.globenewswire.com/Resource/Download/abc")
        self.assertEqual((typ,fmt),("opaque_download","unknown_type_requires_header_check"))
        self.assertEqual(classify_link("https://www.auss.no/investor/results-webcast/2025/annual-report-2025/")[0],"report_landing_page")
        self.assertEqual(classify_link("https://www.auss.no/content/file.PDF"),("direct_file","pdf"))


if __name__=="__main__":
    unittest.main()
