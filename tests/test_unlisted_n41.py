"""N41 seed page contracts: original research links, not quote promotion."""
import unittest
from pathlib import Path
from html.parser import HTMLParser
import json
ROOT=Path(__file__).resolve().parents[1]

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.companies=[]
        self.events=[]
        self.urls=[]
        self.ids=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if "id" in a:self.ids.append(a["id"])
        classes=a.get("class","").split()
        if "n41-company" in classes:self.companies.append(a)
        if "n41-event" in classes:self.events.append(a)
        if tag=="a":self.urls.append(a.get("href",""))

class UnlistedTests(unittest.TestCase):
    def setUp(self):
        self.html=(ROOT/"unlisted.html").read_text(encoding="utf-8")
        self.page=Page()
        self.page.feed(self.html)
    def test_initial_company_identity_and_sources(self):
        self.assertEqual({x["id"] for x in self.page.companies},
                         {"neura","agile","sitegeist","sit","anybotics","exotec","saga","wandercraft","1x","robco","lovable","mistral","helsing","monumental","iceye","quantum-systems","alice-bob","rocsys","lely"})
        self.assertEqual(len(self.page.ids),len(set(self.page.ids)))
        self.assertEqual(sum(x["data-kind"]=="Discovery candidate" for x in self.page.companies),14)
        for link in self.page.urls:
            self.assertFalse(link.lower().startswith(("javascript:","data:")))
    def test_monumental_owner_selected(self):
        card=next(x for x in self.page.companies if x["id"]=="monumental")
        self.assertEqual(card["data-kind"],"Company watch")
        self.assertIn("19 company records",self.html)
        self.assertIn("https://www.monumental.nl/blog/we-raised-32-million-to-put-more/",self.page.urls)
    def test_listed_expansion_separate_from_monitored_inventory(self):
        stock=(ROOT/"stocks.html").read_text(encoding="utf-8")
        self.assertEqual(stock.count('class="n41-listed-candidate"'),7)
        self.assertIn("separate from the existing 500 listing inventory",stock)
        for name in ("Exail Technologies","MilDef","KION Group","Jungheinrich","Teradyne","Symbotic","Einride"):
            self.assertIn(name,stock)
        self.assertNotIn('id="einride"',self.html)
    def test_listing_types_separated(self):
        self.assertEqual({x["data-kind"] for x in self.page.events},
                         {"Initial public offering","Spin-off admission","IPO / listing application","Additional listing","Reported IPO intent"})
        self.assertIn("Already listed on Nasdaq Riga since 2022",self.html)
        self.assertIn("trading not yet confirmed",self.html)
        self.assertIn("not an automatically refreshed news feed",self.html)
        self.assertIn("listing status review pending",self.html)
        self.assertNotIn('id="indexo"',self.html)
    def test_recent_listing_handoff_is_not_private_or_quote_monitored(self):
        self.assertIn("hasko-handoff",self.page.ids)
        self.assertNotIn("hasko-handoff",{x["id"] for x in self.page.companies})
        self.assertIn("SE0021308566",self.html)
        self.assertIn("conditional when-issued period through 26 November",self.html)
        self.assertIn("not yet a Stockwatch price-monitored listing",self.html)
        self.assertIn("b00d4d16d1670fc9bcbf3013dc2654292",self.html)
    def test_assets_explicitly_public_and_shared_nav(self):
        manifest=json.loads((ROOT/"scripts/public-pages-manifest-v122.json").read_text())
        for p in ("unlisted.html","unlisted-n41.css","unlisted-n41.js","shell-v47.js"):
            self.assertIn(p,manifest["files"])
            self.assertTrue((ROOT/p).is_file())
        self.assertIn("Unlisted Companies",(ROOT/"shell-v47.js").read_text(encoding="utf-8"))
        self.assertIn("unlisted-n41.js",self.html)
        self.assertIn("shell-v47.js",self.html)

if __name__=="__main__":unittest.main()
