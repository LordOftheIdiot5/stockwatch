from html.parser import HTMLParser
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
PAGES="index stocks company compare terminal directory research intelligence price-history spreads news calendar shorts commodities shipping health welcome".split()
class Markup(HTMLParser):
    def __init__(self): super().__init__();self.links=[];self.mobile=0;self.css=False;self.ids=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);self.ids.extend([a["id"]] if "id" in a else [])
        if tag=="a":self.links.append(a.get("href"))
        if tag=="nav" and a.get("class")=="sw-mobile-nav":self.mobile+=1
        if tag=="link" and a.get("href","").startswith("shell-v47.css"):self.css=True
class ShellTests(unittest.TestCase):
    def test_all_routes(self):
        for page in PAGES:
            with self.subTest(page=page):
                p=Markup();p.feed((ROOT/(page+".html")).read_text(encoding="utf-8"))
                self.assertEqual(p.mobile,1);self.assertTrue(p.css)
                self.assertTrue(set(x+".html" for x in PAGES if x!="company")<=set(p.links))
                self.assertEqual(len(p.ids),len(set(p.ids)))
    def test_no_broken_local_nav(self):
        for page in PAGES:self.assertTrue((ROOT/(page+".html")).exists())
if __name__=="__main__":unittest.main()
