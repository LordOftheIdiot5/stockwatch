"""Official Nasdaq Nordic RSS: strict metadata, no incorrect price/issuer links."""
import json,sys,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from email.utils import format_datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import nasdaq_nordic_notices as n

NOW=datetime(2026,11,21,9,tzinfo=timezone.utc)
URL="https://view.news.eu.nasdaq.com/view?id=0066&lang=en"
def stamp(days=0):
    return format_datetime(NOW-timedelta(days=days))
def sample(rows):
    return ('<?xml version="1.0"?><rss version="2.0"><channel><title>Nasdaq</title>'+
      ''.join('<item><title>'+title+'</title><link>'+url.replace('&','&amp;')+
      '</link><pubDate>'+published+'</pubDate></item>' for title,url,published in rows)+
      '</channel></rss>').encode()

class TestOfficialNordicNotices(unittest.TestCase):
    def test_original_metadata_and_no_issuer_inference(self):
        feed=sample([("Original exchange notice",URL,stamp()),
           ("Hostile", "https://evil.example/news",stamp()),
           ("Older", "https://view.news.eu.nasdaq.com/view?id=old",stamp(181)),
           ("Impossible future", "https://view.news.eu.nasdaq.com/view?id=next",stamp(-2))])
        found=n.parse("nordicInvestorNews",feed,NOW)
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]["url"],URL)
        self.assertEqual(found[0]["issuerMatch"],"not_established")
        self.assertIsNone(found[0]["regulatory"])
        self.assertNotIn("ticker",found[0])
        self.assertNotIn("content",found[0])
        for bad in ("http://view.news.eu.nasdaq.com/a","https://view.news.eu.nasdaq.com.evil.example/a","https://user@view.news.eu.nasdaq.com/a"):
            self.assertFalse(n.allowed(bad))
        with self.assertRaises(ValueError):
            n.parse("unknown",feed,NOW)
        with self.assertRaises(Exception):
            n.parse("nordicInvestorNews",b'<!DOCTYPE rss [<!ENTITY bad SYSTEM "file:///etc/passwd">]><rss>&bad;</rss>',NOW)

    def test_failure_preserves_original_time_and_success_time(self):
        xml=sample([("Quarterly notice",URL,stamp())])
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);calls=[]
            def good(url): calls.append(url);return xml
            a=n.build(root,NOW,good)
            self.assertEqual(len(calls),2)
            self.assertEqual(len(a["items"]),1)
            self.assertEqual(a["items"][0]["published"],n.iso(NOW))
            self.assertEqual(a["status"],"ok")
            def fail(url): raise TimeoutError()
            b=n.build(root,NOW+timedelta(hours=1),fail)
            self.assertEqual(b["status"],"degraded")
            self.assertEqual(b["items"],a["items"])
            self.assertEqual(b["sources"]["nordicInvestorNews"]["lastSuccess"],n.iso(NOW))
            self.assertEqual(b["sources"]["nordicInvestorNews"]["lastAttempt"],n.iso(NOW+timedelta(hours=1)))
            self.assertEqual(json.loads((root/n.OUTPUT).read_text())["items"],b["items"])

    def test_stale_retained_pruned_and_invalid_xml_rejected(self):
        with self.assertRaises(ValueError):
            n.parse("nordicInvestorNews",b"<html>not rss</html>",NOW)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            first=n.build(root,NOW,lambda _:sample([("Old",URL,stamp(179))]))
            self.assertEqual(len(first["items"]),1)
            later=n.build(root,NOW+timedelta(days=3),lambda _:sample([]))
            self.assertFalse(later["items"])
            self.assertEqual(later["sources"]["nordicInvestorNews"]["status"],"ok")
        self.assertEqual(n.parse("nordicInvestorNews",sample([("Bad","",stamp())]),NOW),[])
        with self.assertRaises(ValueError):
            n.parse("nordicInvestorNews",b"x"*(n.MAX_BYTES+1),NOW)
