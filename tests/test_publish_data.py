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

    def test_invalid_catalog_falls_back_safely(self):
        result=json.loads(publish_data.merge_catalog(b"not-json",self.incoming,"official"))
        self.assertEqual(len(result["datasets"]),2)
        self.assertEqual({x["path"] for x in result["datasets"]},
                         {"data/economic-feeds.json","data/shipping-open.json"})

if __name__=="__main__":
    unittest.main()
