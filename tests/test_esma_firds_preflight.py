import sys,unittest
from pathlib import Path
from datetime import date,datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from esma_firds_preflight import manifest,discover,probe
def row(name):
    return {"file_name":name,"download_link":"http://firds.esma.europa.eu/firds/"+name}
class ManifestTests(unittest.TestCase):
    def test_complete_equity_and_delta_sets(self):
        rows=[row("FULINS_E_20261114_02of02.zip"),row("FULINS_E_20261114_01of02.zip"),row("DLTINS_20261119_01of01.zip"),row("FULINS_D_20261114_01of01.zip")]
        groups=manifest(rows)
        self.assertEqual(len(groups),2)
        self.assertTrue(all(g["complete"] for g in groups))
        self.assertTrue(all(f["url"].startswith("https://") for g in groups for f in g["files"]))
    def test_incomplete_and_duplicate_rejected(self):
        r=row("FULINS_E_20261114_01of02.zip")
        self.assertFalse(manifest([r])[0]["complete"])
        with self.assertRaisesRegex(ValueError,"duplicate"):manifest([r,r])
        with self.assertRaisesRegex(ValueError,"inconsistent"):manifest([r,row("FULINS_E_20261114_02of03.zip")])
    def test_untrusted_link(self):
        r=row("FULINS_E_20261114_01of01.zip");r["download_link"]=r["download_link"].replace("firds.esma.europa.eu","example.org")
        with self.assertRaises(ValueError):manifest([r])
    def test_registry_pagination_and_probe(self):
        docs=[row("FULINS_D_20261114_01of01.zip")]*100+[row("FULINS_E_20261114_01of01.zip")]
        def fetch(url):
            from urllib.parse import parse_qs,urlsplit
            start=int(parse_qs(urlsplit(url).query)["start"][0])
            return {"responseHeader":{"status":0},"response":{"numFound":len(docs),"start":start,"docs":docs[start:start+100]}}
        self.assertEqual(len(discover(date(2026,11,7),date(2026,11,20),fetch)),101)
        result=probe(datetime(2026,11,20,tzinfo=timezone.utc),fetch)
        self.assertEqual(result["instrumentRecordsImported"],0)
        self.assertEqual(result["latestEquityFullSet"]["date"],"2026-11-14")
