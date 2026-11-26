"""Unit checks for two GitHub workflows updating separate data sets on main."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import publish_data


class PublishDataTests(unittest.TestCase):
    def setUp(self):
        self.remote = json.dumps({"generated":"2026-11-13T18:00:00Z","datasets":[
            {"path":"data/economic-feeds.json","records":4},
            {"path":"data/shipping-open.json","records":0},
            {"path":"data/news-latest.json","records":100},
            {"path":"data/source-health.json","records":138},
        ]}).encode()
        self.incoming = json.dumps({"generated":"2026-11-13T18:01:00Z","datasets":[
            {"path":"data/economic-feeds.json","records":6},
            {"path":"data/shipping-open.json","records":340},
            {"path":"data/news-latest.json","records":90},
        ]}).encode()

    def test_official_refresh_preserves_newest_scanner_entries(self):
        merged=json.loads(publish_data.merge_catalog(self.remote,self.incoming,"official"))
        records={x["path"]:x["records"] for x in merged["datasets"]}
        self.assertEqual(records["data/economic-feeds.json"],6)
        self.assertEqual(records["data/shipping-open.json"],340)
        self.assertEqual(records["data/news-latest.json"],100)
        self.assertEqual(records["data/source-health.json"],138)

    def test_scanner_refresh_preserves_latest_official_sources(self):
        merged=json.loads(publish_data.merge_catalog(self.remote,self.incoming,"scan"))
        records={x["path"]:x["records"] for x in merged["datasets"]}
        self.assertEqual(records["data/economic-feeds.json"],4)
        self.assertEqual(records["data/shipping-open.json"],0)
        self.assertEqual(records["data/news-latest.json"],90)
        self.assertEqual(records["data/source-health.json"],138)

    def test_worldbank_port_refresh_is_official_only(self):
        remote=json.dumps({"datasets":[
            {"path":"data/shipping-ports.json","records":4},
            {"path":"data/news-latest.json","records":100},
        ]}).encode()
        incoming=json.dumps({"datasets":[
            {"path":"data/shipping-ports.json","records":240},
            {"path":"data/news-latest.json","records":10},
        ]}).encode()
        official=json.loads(publish_data.merge_catalog(remote,incoming,"official"))
        scanner=json.loads(publish_data.merge_catalog(remote,incoming,"scan"))
        self.assertEqual({x["path"]:x["records"] for x in official["datasets"]},
                         {"data/shipping-ports.json":240,"data/news-latest.json":100})
        self.assertEqual({x["path"]:x["records"] for x in scanner["datasets"]},
                         {"data/shipping-ports.json":4,"data/news-latest.json":10})

    def test_unctad_connectivity_treated_as_official_source(self):
        remote=json.dumps({"datasets":[
            {"path":"data/shipping-connectivity.json","records":20},
            {"path":"data/news-latest.json","records":100},
        ]}).encode()
        incoming=json.dumps({"datasets":[
            {"path":"data/shipping-connectivity.json","records":350},
            {"path":"data/news-latest.json","records":1},
        ]}).encode()
        official=json.loads(publish_data.merge_catalog(remote,incoming,"official"))
        scanned=json.loads(publish_data.merge_catalog(remote,incoming,"scan"))
        self.assertEqual({x["path"]:x["records"] for x in official["datasets"]},
                         {"data/shipping-connectivity.json":350,"data/news-latest.json":100})
        self.assertEqual({x["path"]:x["records"] for x in scanned["datasets"]},
                         {"data/shipping-connectivity.json":20,"data/news-latest.json":1})

    def test_invalid_catalog_falls_back_safely(self):
        result=json.loads(publish_data.merge_catalog(b"not-json",self.incoming,"official"))
        self.assertEqual(len(result["datasets"]),2)
        self.assertEqual({x["path"] for x in result["datasets"]},
                         {"data/economic-feeds.json","data/shipping-open.json"})

class SignalPublicationTests(unittest.TestCase):
    def test_complete_failure_keeps_dated_changes_but_never_redates(self):
        row={"ticker":"AAA","name":"Example","currency":"NOK","date":"2026-11-17","close":12,"volume":100,"changePct":3,"priceStatus":"reported"}
        old={"generated":"2026-11-17T20:00:00Z","companies":[row]}
        new={"generated":"2026-11-18T00:00:00Z","companies":[{**row,"priceStatus":"retained"}]}
        wl={"tickers":[{"ticker":"AAA"}]}
        encode=lambda x:json.dumps(x).encode()
        self.assertEqual(publish_data.guarded_signals(encode(new),encode(old),encode(wl)),encode(new))
        for bad in ([],[{**row,"volume":0}],[{**row,"close":None}],[{**row,"date":"2026-11-16"}],[row,row]):
            with self.assertRaises(ValueError):
                publish_data.guarded_signals(encode({**new,"companies":bad}),encode(old),encode(wl))
        with self.assertRaises(ValueError):
            publish_data.guarded_signals(encode({**new,"generated":"2026-11-16T20:00:00Z"}),encode(old),encode(wl))
        with self.assertRaises(ValueError):
            publish_data.guarded_signals(b"corrupt",encode(old),encode(wl))


class UnlistedPublicationTests(unittest.TestCase):
    def setUp(self):
        self.registry={"companies":[{"id":"neura","aliases":["NEURA Robotics"]},{"id":"mistral","aliases":["Mistral AI"]}]}
    def row(self, company, name, suffix, day="2026-11-25"):
        return {"company":company,"title":name+" announcement "+suffix,"url":"https://news.google.com/rss/articles/"+suffix,
                "publisher":"Fixture publisher","date":day+"T12:00:00+00:00","tier":"named reference","id":"fixture"}
    def doc(self, at, rows, status):
        return {"schema":1,"attemptedAt":at,"items":rows,"coverage":{c["id"]:{"status":status,"freshNamedReferences":0,"retainedReferences":0} for c in self.registry["companies"]}}
    def merge(self,new,old):
        enc=lambda x:json.dumps(x).encode()
        return json.loads(publish_data.merge_unlisted_news(enc(new),enc(old),enc(self.registry)))
    def test_failed_newer_scan_retains_remote_news(self):
        a=self.row("neura","NEURA Robotics","one")
        b=self.row("mistral","Mistral AI","two")
        old=self.doc("2026-11-26T03:05:00+00:00",[a,b],"named_references_observed")
        new=self.doc("2026-11-26T03:13:00+00:00",[a],"provider_skipped_after_error")
        result=self.merge(new,old)
        self.assertEqual(len(result["items"]),2)
        self.assertEqual(result["coverage"]["mistral"]["retainedReferences"],1)
        self.assertEqual(result["coverage"]["mistral"]["freshNamedReferences"],0)
        self.assertEqual(result["coverage"]["mistral"]["status"],"provider_skipped_after_error")
        self.assertEqual(result["attemptedAt"],new["attemptedAt"])
    def test_old_attempt_cannot_replace_new_health(self):
        a=self.row("neura","NEURA Robotics","one")
        b=self.row("neura","NEURA Robotics","two")
        old=self.doc("2026-11-26T04:00:00+00:00",[b],"named_references_observed")
        new=self.doc("2026-11-26T03:00:00+00:00",[a],"unconfirmed")
        r=self.merge(new,old)
        self.assertEqual(r["attemptedAt"],old["attemptedAt"])
        self.assertEqual(r["coverage"]["neura"]["status"],"named_references_observed")
        self.assertEqual(len(r["items"]),2)
    def test_expiry_identity_url_and_duplicate_boundaries(self):
        rows=[self.row("neura","NEURA Robotics",str(i)) for i in range(20)]
        rows.extend([self.row("neura","NEURA Robotics","expired","2026-10-01"),
                     self.row("neura","NEURA Robotics","future","2026-11-27"),
                     self.row("removed","NEURA Robotics","removed"),
                     self.row("mistral","Different company","wrong"),
                     {**self.row("mistral","Mistral AI","evil"),"url":"https://evil.invalid/article"}])
        old=self.doc("2026-11-26T03:00:00+00:00",rows,"unconfirmed")
        new=self.doc("2026-11-26T04:00:00+00:00",[rows[0]],"unconfirmed")
        r=self.merge(new,old)
        self.assertEqual(len(r["items"]),15)
        self.assertEqual(r["coverage"]["mistral"]["retainedReferences"],0)
        self.assertEqual(len({x["id"] for x in r["items"]}),15)
        self.assertTrue(all(x["company"]=="neura" and x["date"].startswith("2026-11-25") for x in r["items"]))

if __name__=="__main__":
    unittest.main()
