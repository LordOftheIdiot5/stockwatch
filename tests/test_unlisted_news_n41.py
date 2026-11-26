import json
import sys
import unittest
from urllib.error import HTTPError
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import unlisted_news_n41 as n

NOW=datetime(2026,11,25,18,tzinfo=timezone.utc)
COMP={"id":"sit","aliases":["Swedish Implant Technology"]}
def raw(title="Swedish Implant Technology reports funding",url="https://news.google.com/rss/articles/fixture",published="Wed, 25 Nov 2026 12:00:00 GMT"):
    return {"title":title,"url":url,"publisher":"Fixture publisher","published":published}

class UnlistedNewsTests(unittest.TestCase):
    def test_identity_and_safe_url(self):
        self.assertIsNotNone(n.candidate(COMP,raw(),NOW))
        for item in (raw("SIT wins a match"),raw(url="https://evil.example/rss/articles/fixture"),
                     raw(url="https://news.google.com@evil.example/rss/articles/fixture"),
                     raw(published="Thu, 26 Nov 2026 12:00:00 GMT"),
                     raw(published="Thu, 01 Oct 2026 12:00:00 GMT")):
            self.assertIsNone(n.candidate(COMP,item,NOW))
    def test_duplicates_and_failure_retains_dated_references(self):
        reg={"companies":[COMP]}
        doc=n.collect(reg,{},lambda *a,**k:[raw(),raw(url="https://news.google.com/rss/articles/second")],NOW)
        self.assertEqual(len(doc["items"]),1)
        self.assertEqual(doc["items"][0]["tier"],"named reference")
        def fail(*a,**k):raise OSError("fixture failure")
        recovered=n.collect(reg,doc,fail,NOW)
        self.assertEqual(recovered["items"],doc["items"])
        self.assertEqual(recovered["coverage"]["sit"]["status"],"unconfirmed")
        self.assertEqual(recovered["coverage"]["sit"]["freshNamedReferences"],0)
    def test_provider_503_stops_remaining_queries(self):
        calls=[]
        def fail(*a,**k):
            calls.append(a)
            raise HTTPError("",503,"fixture",{},None)
        doc=n.collect({"companies":[COMP,{"id":"other","aliases":["Other company"]}]},{},fail,NOW)
        self.assertEqual(len(calls),1)
        self.assertEqual(doc["coverage"]["sit"]["status"],"provider_http_error")
        self.assertEqual(doc["coverage"]["other"]["status"],"provider_skipped_after_error")
        self.assertEqual(doc["coverage"]["other"]["httpStatus"],503)
    def test_empty_is_not_verified_no_news(self):
        d=n.collect({"companies":[COMP]}, {}, lambda *a,**k:[],NOW)
        self.assertEqual(d["coverage"]["sit"]["status"],"no_usable_results_or_unconfirmed")
    def test_monumental_requires_robotics_context(self):
        company=next(c for c in json.loads(n.SEED.read_text(encoding="utf-8"))["companies"] if c["id"]=="monumental")
        self.assertIsNotNone(n.candidate(company,raw("Monumental Robotics expands fleet"),NOW))
        self.assertIsNone(n.candidate(company,raw("A monumental achievement for construction"),NOW))
        self.assertIsNone(n.candidate(company,raw("Monumental Sports announces new deal"),NOW))
    def test_reviewed_seed_covers_all_companies_and_assets(self):
        d=json.loads(n.SEED.read_text(encoding="utf-8"))
        self.assertEqual({x["id"] for x in d["companies"]},{x["company"] for x in d["items"]})
        self.assertEqual(len(d["items"]),27)
        self.assertEqual(len({x["id"] for x in d["items"]}),27)
        self.assertTrue(all(x["url"].startswith("https://") and x["date"]<=d["reviewed"] for x in d["items"]))
        manifest=json.loads((ROOT/"scripts/public-pages-manifest-v122.json").read_text())
        for path in (n.SEED,n.OUTPUT):self.assertIn(path.relative_to(ROOT).as_posix(),manifest["files"])
if __name__=="__main__":unittest.main()
