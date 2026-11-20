import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from cboe_nordic_coverage import scope,audit
R={"id":"registry:XSTO:BBG000BXRMY9","mic":"XSTO","figi":"BBG000BXRMY9"}
C={"listingId":R["id"],"mic":"XSTO","figi":R["figi"],"isin":"SE0000108656","status":"exact_candidate_join","reviewRequired":True,"pricePublicationAllowed":False}
Q={"queues":{"nasdaq_nordic":{"records":[R]}}}
class Tests(unittest.TestCase):
    def test_scope(self):
        g,n=scope(Q,[C])
        self.assertEqual(n,1)
        self.assertEqual(g["XSTO"],{(C["isin"],"XSTO")})
    def test_conflicting_candidate(self):
        for bad in ({**C,"mic":"XCSE"},{**C,"pricePublicationAllowed":True},{**C,"figi":"WRONG"}):
            with self.assertRaises(ValueError):scope(Q,[bad])
    def test_duplicate(self):
        with self.assertRaises(ValueError):scope(Q,[C,C])
    def test_reference_is_not_price(self):
        raw=b"environment=PROD,created=2026-11-20\nisin,mic,currency,live,asset_class\nSE0000108656,XSTO,SEK,t,EQTY\n"
        a=audit(Q,[C],download=lambda:raw)
        self.assertEqual(a["matched"],1)
        self.assertEqual(a["pricesCollected"],0)
        self.assertFalse(a["primaryCloseEstablished"])
