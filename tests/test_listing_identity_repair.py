import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from registered_sources import figi_jobs

class ListingIdentityTests(unittest.TestCase):
    def test_watchlist_migration(self):
        rows=json.loads((ROOT/"watchlist.json").read_text(encoding="utf-8"))["tickers"]
        by={r["ticker"]:r for r in rows}
        self.assertEqual(len(rows),138)
        self.assertEqual(len(by),138)
        self.assertNotIn("CADLR.OL",by)
        self.assertEqual(by["CDLR.OL"]["isin"],"GB00BN49H029")
        self.assertEqual(by["CDLR.OL"]["previousIsin"],"DK0061412772")
        self.assertEqual(by["CDLR.OL"]["historyPolicy"],"separate_predecessor_security")
        self.assertNotIn("medianVolume",by["CDLR.OL"])
    def test_explicit_venue_overrides_suffix(self):
        rows=[{"ticker":"BLUE.ST","isin":"SE0015382148","mic":"NSME"},{"ticker":"SHT-B.ST","isin":"SE0016843809","mic":"XSAT"},{"ticker":"KLDVK.OL","isin":"NO0010884794","mic":"MERK"}]
        jobs=dict(figi_jobs({"entities":rows}))
        self.assertEqual([jobs[r["ticker"]]["micCode"] for r in rows],["NSME","XSAT","MERK"])
        self.assertTrue(all(j["idType"]=="ID_ISIN" for j in jobs.values()))

if __name__=="__main__": unittest.main()
