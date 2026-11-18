import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from last_known import company_row,context_rows
from price_freshness import price_quality
class LastKnown(unittest.TestCase):
    def setUp(self):
        self.entry=dict(ticker="AAA",name="Example",sector="Energy")
        self.old={**self.entry,"date":"2026-11-16","close":12,"currency":"NOK","volume":100,"changePct":2,"sigma":1,"rvol":1,"stories":[{"fresh":True}],"priceObservedAt":"2026-11-16T21:00:00Z"}
    def row(self,fresh=None,old=None,entry=None):
        return company_row(entry or self.entry,fresh,self.old if old is None else old,"2026-11-17","2026-11-17T18:00:00Z","2026-11-16T21:00:00Z")
    def test_failure_retains_original_date_and_disables_signal(self):
        r=self.row()
        self.assertEqual(r["close"],12)
        self.assertEqual(r["date"],self.old["date"])
        self.assertEqual(r["priceObservedAt"],self.old["priceObservedAt"])
        self.assertEqual(r["priceStatus"],"retained")
        self.assertEqual(r["stories"],[])
        self.assertNotEqual(price_quality(r,"2026-11-16"),"comparable")
        self.assertEqual(self.row(old=r)["priceObservedAt"],r["priceObservedAt"])
    def test_no_identity_bridge_or_fake_price(self):
        r=self.row(entry={**self.entry,"name":"Other security"})
        self.assertTrue(r["unavailable"])
        self.assertNotIn("close",r)
        self.assertTrue(self.row(entry={**self.entry,"isin":"NEW"})["unavailable"])
    def test_regression_and_recovery(self):
        self.assertEqual(self.row(fresh={**self.old,"date":"2026-11-15"})["date"],self.old["date"])
        r=self.row(fresh={**self.old,"date":"2026-11-17","close":13})
        self.assertEqual(r["priceStatus"],"reported")
        self.assertEqual(r["close"],13)
    def test_partial_same_session_does_not_destroy_valid_movement(self):
        for incomplete in ({"volume":0},{"changePct":None},{"volume":None}):
            row=self.row(fresh={**self.old,**incomplete,"close":13})
            self.assertEqual(row["priceStatus"],"retained")
            self.assertEqual(row["date"],self.old["date"])
            self.assertEqual(row["close"],self.old["close"])
            self.assertEqual(row["changePct"],self.old["changePct"])
            self.assertEqual(row["volume"],self.old["volume"])
        # Never relabel yesterday's change as a newer trading session.
        row=self.row(fresh={**self.old,"date":"2026-11-17","volume":0,"changePct":0})
        self.assertEqual(row["date"],"2026-11-17")
        self.assertEqual(row["volume"],0)
    def test_context_retained_original_date(self):
        old=[dict(ticker="BDRY",unit="USD",date="2026-11-16",last=10)]
        r=context_rows([],old,"freight","new","old","2026-11-17")
        self.assertEqual(r[0]["date"],"2026-11-16")
        self.assertEqual(r[0]["observationStatus"],"retained")
        self.assertEqual(r[0]["observedAt"],"old")
        self.assertEqual(context_rows([], [dict(ticker="BDRY",unit="USD",last=10)],"freight","new","old","2026-11-17"),[])

    def test_older_valid_move_survives_new_zero_volume_without_mixing_prices(self):
        fresh={**self.old,"date":"2026-11-17","close":13,"volume":0,"changePct":0}
        r=self.row(fresh=fresh)
        self.assertEqual(r["close"],13)
        self.assertEqual(r["changePct"],0)
        self.assertEqual(r["lastValidMovement"]["close"],12)
        self.assertEqual(r["lastValidMovement"]["date"],"2026-11-16")
        self.assertEqual(r["lastValidMovement"]["changePct"],2)
        retained=self.row(old=r)
        self.assertEqual(retained["lastValidMovement"],r["lastValidMovement"])
        recovered=self.row(fresh={**fresh,"volume":100,"changePct":3},old=r)
        self.assertNotIn("lastValidMovement",recovered)
    def test_seed_requires_exact_identity_and_older_date(self):
        fresh={**self.old,"date":"2026-11-17","close":13,"volume":0,"changePct":0}
        def seeded(seed):
            return company_row(self.entry,fresh,None,"2026-11-17","new","old",seed)
        self.assertEqual(seeded(self.old)["lastValidMovement"]["changePct"],2)
        for bad in ({"currency":"SEK"},{"name":"Other"},{"ticker":"OTHER"},{"date":"2026-11-17"},{"volume":0},{"isin":"OTHER"}):
            self.assertNotIn("lastValidMovement",seeded({**self.old,**bad}))
