"""V101 original issuer IR discovery validation: no fabricated issuer data or document downloads."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from issuer_ir_reports_v101 import discover, hostname, merge, run, validate_registry

BASE = {
    "ticker": "SALM.OL", "issuer": "SalMar ASA",
    "landingPage": "https://www.salmar.no/en/investor/reports-presentations/",
    "evidenceUrl": "https://www.salmar.no/en/investor/reports-presentations/",
    "allowedHosts": ["www.salmar.no", "ml-eu.globenewswire.com"],
    "documentRetentionApproved": False,
    "publicDocumentDisplayApproved": False
}

HTML = """<html><body>
<h2>Quarterly Financial Reports 2026</h2>
<a href="/reports/SalMar_Q1_2026.pdf">SalMar Q1 2026 - Report Download</a>
<a href="/reports/SalMar_Q1_2026.pdf">Duplicate official report</a>
<a href="https://unknown.example/2026-annual-report.pdf">External unrelated report</a>
<h2>Annual Reports</h2>
<a href="https://ml-eu.globenewswire.com/salmar-annual-report-2025.pdf">27.03.26 SalMar Annual Report 2025 Download</a>
<a href="javascript:alert(1)">Annual report 2025</a>
<a href="//evil.example/2026-annual-report.pdf">PDF</a>
<h2>Contact and careers</h2>
<a href="/careers">Contact</a>
<script><a href="/fake/annual-report-2026.pdf">false</a></script>
</body></html>"""


class IssuerIRV101Tests(unittest.TestCase):
    def test_manifest_is_exact_domain_and_all_rights_denied(self):
        data = {"schemaVersion": 1, "sources": [copy.deepcopy(BASE)]}
        self.assertEqual(len(validate_registry(data)), 1)
        bad = copy.deepcopy(data)
        bad["sources"][0]["documentRetentionApproved"] = True
        with self.assertRaisesRegex(ValueError, "permissions"):
            validate_registry(bad)
        bad = copy.deepcopy(data)
        bad["sources"][0]["landingPage"] = "http://www.salmar.no/"
        with self.assertRaisesRegex(ValueError, "domain"):
            validate_registry(bad)
        bad = copy.deepcopy(data)
        bad["sources"][0]["ticker"] = ""
        with self.assertRaises(ValueError):
            validate_registry(bad)

    def test_reject_private_url_and_cross_origin_links(self):
        for url in ("https://localhost/private", "https://127.0.0.1/",
                    "http://www.salmar.no/", "https://user:password@www.salmar.no/x",
                    "https://www.salmar.no:1234/", "https://192.168.1.1/"):
            self.assertEqual(hostname(url), "")
        records = discover(HTML, BASE)
        self.assertEqual(len(records), 2)
        urls = [r["documentUrl"] for r in records]
        self.assertTrue(all(u.startswith("https://") for u in urls))
        self.assertFalse(any("unknown.example" in u or "evil.example" in u for u in urls))

    def test_classification_no_inferred_financial_values(self):
        records = discover(HTML, BASE)
        by_kind = {r["kindCandidate"]: r for r in records}
        self.assertEqual(set(by_kind), {"annual_report", "interim_report"})
        self.assertEqual(by_kind["interim_report"]["quarterCandidate"], 1)
        self.assertEqual(by_kind["interim_report"]["fiscalYearCandidate"], 2026)
        self.assertEqual(by_kind["annual_report"]["fiscalYearCandidate"], 2025)
        for r in records:
            self.assertIsNone(r["publishedAt"])
            self.assertEqual(r["state"], "candidate_requires_review")
            self.assertFalse(r["documentDownloaded"])
            self.assertFalse(r["privateRetentionApproved"])
            self.assertFalse(r["publicDocumentDisplayApproved"])
            self.assertNotIn("revenue", r)
            self.assertEqual(len(r["id"]), 24)

    def test_failed_ir_fetch_preserves_previous_candidates(self):
        previously = discover(HTML, BASE)
        previous = {"items": previously}
        def failed_fetch(url, hosts):
            raise OSError("network failed")
        result = run({"schemaVersion": 1, "sources": [BASE]}, previous,
                     fetch=failed_fetch, permit=lambda url,hosts: True,
                     timestamp="2026-11-21T09:00:00Z")
        self.assertEqual(result["candidateCount"], len(previously))
        self.assertEqual(result["freshCandidateCount"], 0)
        self.assertEqual(result["attempts"][0]["status"], "failed")
        self.assertEqual(result["items"], previously)

    def test_robots_disallow_skips_html_request(self):
        def forbidden_fetch(url, hosts):
            self.fail("Fetch must not be called if robots reject the page")
        r = run({"schemaVersion": 1, "sources": [BASE]},
                fetch=forbidden_fetch, permit=lambda url,hosts: False)
        self.assertEqual(r["freshCandidateCount"], 0)
        self.assertEqual(r["attempts"][0]["reason"], "robots_disallowed_or_unavailable")

    def test_successful_fetch_is_metadata_only(self):
        r = run({"schemaVersion": 1, "sources": [BASE]},
                fetch=lambda url,hosts: HTML, permit=lambda url,hosts: True,
                timestamp="2026-11-21T09:00:00Z")
        self.assertEqual(r["candidateCount"], 2)
        self.assertEqual(r["attempts"][0]["status"], "completed")
        self.assertIn("No report bytes downloaded", r["notice"])
        self.assertEqual(len(merge(r["items"], r["items"])), 2)

    def test_real_manifest_stays_unapproved_and_ticker_join_is_grounded(self):
        data = json.loads((ROOT / "scripts/issuer_ir_sources_v101.json").read_text())
        rows = validate_registry(data)
        tickers = {r["ticker"] for r in json.loads((ROOT / "watchlist.json").read_text())["tickers"]}
        self.assertTrue(all(row["ticker"] in tickers for row in rows))
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row["documentRetentionApproved"] is False for row in rows))


if __name__ == "__main__":
    unittest.main()
