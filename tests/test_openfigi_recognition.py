import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class Recognition(unittest.TestCase):
    def test_pages_link_to_exact_listing_without_licence_claim(self):
        for file in ("welcome.html","research.html"):
            markup=(ROOT/file).read_text(encoding="utf-8")
            self.assertEqual(markup.count('id="openfigi-facilitator"'),1)
            self.assertIn('href="https://www.openfigi.com/about/facilitators/third-parties/nordl"',markup)
            self.assertIn("does not establish a Bloomberg market-data licence",markup)
