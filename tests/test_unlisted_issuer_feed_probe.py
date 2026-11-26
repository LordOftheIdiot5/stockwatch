import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import unlisted_issuer_feed_probe as p

def sample(link="https://neura-robotics.com/update/",date="Wed, 25 Nov 2026 12:00:00 GMT"):
    return f"""<rss version="2.0"><channel><item><title>Private fixture text</title><link>{link}</link><pubDate>{date}</pubDate><description>Private fixture body</description></item></channel></rss>""".encode()

class IssuerFeedProbeTests(unittest.TestCase):
    def test_metadata_only(self):
        r=p.probe("neura",lambda _:sample())
        self.assertEqual(r,{"status":"rss_observed","itemCount":1,"sameOriginDatedCount":1})
        self.assertNotIn("fixture",str(r))
        self.assertNotIn("https",str(r))
    def test_invalid_links_and_dates_not_counted(self):
        for raw in (sample("https://evil.example/update"),sample("https://neura-robotics.com@evil.example/update"),sample(date="invalid"),sample(date="25 Nov 2026 12:00:00")):
            self.assertEqual(p.probe("neura",lambda _:raw)["sameOriginDatedCount"],0)
    def test_reject_unsafe_xml_and_html(self):
        for raw in (b"<html/>",b"<!DOCTYPE rss [<!ENTITY x 'secret'>]><rss><channel>&x;</channel></rss>",b"x"*(p.MAX_BYTES+1)):
            self.assertEqual(p.probe("neura",lambda _:raw),{"status":"unconfirmed"})
    def test_http_error_and_endpoint_allowlist(self):
        def fail(_):raise HTTPError("",503,"fixture",{},None)
        self.assertEqual(p.probe("neura",fail),{"status":"http_error","httpStatus":503})
        with self.assertRaises(ValueError):p.fetch("https://evil.example/feed")
if __name__=="__main__":unittest.main()
