"""Guard the production SEO manifest and canonical metadata."""
import unittest
from pathlib import Path
from html.parser import HTMLParser
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
HOST = "https://stocks.nordl.dev/"
PAGES = ["index.html","welcome.html","terminal.html","stocks.html","compare.html","news.html","calendar.html","spreads.html","shipping.html","commodities.html","shorts.html","intelligence.html","directory.html","price-history.html","research.html","health.html","data-products.html"]

class Head(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_head = False
        self.canonicals = []
        self.robots = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "head":
            self.in_head = True
        if self.in_head and tag == "link" and attrs.get("rel", "").lower() == "canonical":
            self.canonicals.append(attrs.get("href"))
        if self.in_head and tag == "meta" and attrs.get("name", "").lower() in ("robots", "googlebot"):
            self.robots.append(attrs.get("content", "").lower())
    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False

class TestPublicSEO(unittest.TestCase):
    def test_sitemap_is_exact_public_allowlist(self):
        root = ET.parse(ROOT / "sitemap.xml").getroot()
        ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        self.assertEqual(root.tag, "{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")
        urls = [e.text for e in root.findall("s:url/s:loc", ns)]
        self.assertEqual(urls, [HOST + ("" if p == "index.html" else p) for p in PAGES])
        self.assertEqual(len(set(urls)), len(urls))
    def test_each_public_page_has_one_matching_canonical(self):
        for page in PAGES:
            with self.subTest(page=page):
                parser = Head()
                parser.feed((ROOT / page).read_text(encoding="utf-8"))
                self.assertEqual(parser.canonicals, [HOST + ("" if page == "index.html" else page)])
                self.assertFalse(any("noindex" in r or "none" in r for r in parser.robots))
    def test_robots_advertise_sitemap_and_allow_crawling(self):
        self.assertEqual((ROOT / "robots.txt").read_text(encoding="utf-8"), "User-agent: *\nAllow: /\n\nSitemap: " + HOST + "sitemap.xml\n")

if __name__ == "__main__":
    unittest.main()
