import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from price_quality_diagnostics import outcome,summarize
class DiagnosticsTests(unittest.TestCase):
    def test_missing_and_mismatch(self):
        e={"ticker":"TEST"}; row={"priceStatus":"retained"}
        self.assertEqual(outcome(e,None,None,None,row),"no_usable_chart")
        self.assertEqual(outcome(e,{"ticker":"OTHER"},None,None,row),"provider_symbol_mismatch")
        self.assertEqual(outcome(e,None,None,None,row,True),"provider_or_parser_exception")
    def test_older_and_partial(self):
        e={"ticker":"TEST"};d={"ticker":"TEST","currency":"NOK"};p={"date":"2026-11-19","volume":100,"currency":"NOK"};r={"priceStatus":"retained"}
        self.assertEqual(outcome(e,d,{"date":"2026-11-18"},p,r),"provider_older_session")
        self.assertEqual(outcome(e,d,{"date":"2026-11-19","volume":0},p,r),"partial_same_session")
    def test_counts_not_fresh(self):
        row={"ticker":"TEST","exchange":"Oslo","priceStatus":"retained","date":"2026-11-19","volume":100,"priceObservedAt":"2026-11-19T22:30:00+00:00"}
        s=summarize([row],{"TEST":"no_usable_chart"},"2026-11-19")
        self.assertEqual(s["retainedTargetDateObservedAfterCutoff"],1)
        self.assertEqual(s["outcomes"],{"no_usable_chart":1})
        self.assertEqual(row["priceStatus"],"retained")
