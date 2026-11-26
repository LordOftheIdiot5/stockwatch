import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import nasdaq_private_csv_probe as n

HEADER = "TradingDateTime;ISIN;Price;Quantity;MIC;PublicationDateTime;Flags;Extra"
ROW = "fixture-time;PRIVATE-IDENTITY;123.45;10;XSTO;fixture-publication;CANC;private"

class NasdaqPrivateProbeTests(unittest.TestCase):
    def test_schema_only_no_raw_fields_or_values(self):
        r = n.inspect_csv((HEADER + "\n" + ROW + "\n").encode())
        self.assertEqual(r["delimiter"], "semicolon")
        self.assertEqual(r["row_count"], 1)
        self.assertEqual(r["malformed_row_count"], 0)
        self.assertEqual(r["unrecognized_column_count"], 1)
        for value in ("PRIVATE-IDENTITY", "123.45", "fixture-time", "private", "XSTO"):
            self.assertNotIn(value, str(r))
        self.assertFalse(r["provider_schema_verified"])
        self.assertFalse(r["public_publication"])
        self.assertFalse(r["retention_enabled"])

    def test_bom_preamble_and_malformed_width(self):
        r = n.inspect_csv(("\ufefffixture\n" + HEADER + "\nshort;row\n").encode())
        self.assertEqual(r["malformed_row_count"], 1)

    def test_reject_html_binary_and_ambiguous_headers(self):
        for raw in (b"<html>blocked</html>", b"\x00", b"", (HEADER + ";ISIN\n").encode()):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                n.inspect_csv(raw)

    def test_advertised_sample_only_and_no_retention(self):
        calls=[]
        def fetch(url,limit):
            calls.append(url)
            if len(calls)==1:
                return b'<a href="/download/NordicEquity-posttrade-2026-01-02T1200">report</a><a href="https://evil.invalid/NordicEquity-posttrade-2026-01-02T1200">external</a>'
            return (HEADER+"\n"+ROW+"\n").encode()
        r=n.inspect_advertised("nordic",fetch)
        self.assertEqual(calls,[n.NAS_PORTALS["nordic"],"https://tradereports.nasdaq.com/download/NordicEquity-posttrade-2026-01-02T1200"])
        self.assertTrue(r["sample_downloaded"])
        self.assertEqual(r["row_count"],1)
        self.assertFalse(r["retention_enabled"])
        self.assertNotIn("PRIVATE-IDENTITY",str(r))
    def test_no_advertised_file_no_second_request(self):
        calls=[]
        def fetch(url,limit):
            calls.append(url)
            return b"<html><ul></ul></html>"
        r=n.inspect_advertised("baltic",fetch)
        self.assertEqual(calls,[n.NAS_PORTALS["baltic"]])
        self.assertEqual(r["status"],"no_recognized_report_links")
        self.assertFalse(r["public_publication"])
    def test_local_file_outside_repository_only(self):
        with self.assertRaises(ValueError):
            n.inspect_file(n.ROOT / "private.csv")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "sample.csv"
            p.write_text(HEADER + "\n" + ROW + "\n", encoding="utf-8")
            self.assertEqual(n.inspect_file(p)["row_count"], 1)

if __name__ == "__main__":
    unittest.main()
