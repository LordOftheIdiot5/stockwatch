"""V97a: price availability cannot masquerade as completed-session confirmation."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from price_evidence import build, age_bucket

NOW = datetime(2026,11,21,2,tzinfo=timezone.utc)

class PriceEvidenceTests(unittest.TestCase):
    def test_retained_same_date_remains_unconfirmed(self):
        rows = [
          {"ticker":"A","exchange":"Oslo","close":100,"changePct":2,"volume":50,"date":"2026-11-20","priceStatus":"retained"},
          {"ticker":"B","exchange":"Oslo","close":101,"changePct":1,"volume":50,"date":"2026-11-20","priceStatus":"reported"},
          {"ticker":"C","exchange":"Oslo","close":102,"changePct":0,"volume":0,"date":"2026-11-20","priceStatus":"reported"},
          {"ticker":"D","exchange":"Paris","close":90,"changePct":1,"volume":20,"date":"2026-11-19","priceStatus":"reported"}]
        watchlist={"tickers":[{"ticker":x,"exchange":"Oslo","mic":"XOSL" if x=="A" else None} for x in ("A","B","C")]+[{"ticker":"D","exchange":"Paris"},{"ticker":"E","exchange":"Paris"}]}
        snapshot={"companies":rows,"priceDiagnostics":{"byExchange":{"Oslo":{"provider_older_session":1,"reported":2},"Paris":{"provider_older_session":0}}}}
        result=build(snapshot,watchlist,NOW)
        self.assertEqual((result["tracked"],result["priced"],result["micProvided"],result["micMissing"]),(5,4,1,4))
        self.assertEqual(result["comparisonDate"],"2026-11-20")
        oslo=result["byExchange"][0]
        self.assertEqual(oslo["quality"],{"comparable":1,"unconfirmed":1,"older":0,"no_volume":1,"unavailable":0})
        self.assertEqual((oslo["retainedTargetDate"],oslo["providerOlderSession"]),(1,1))
        self.assertEqual(result["ageCalendarDays"]["targetDate"],3)
        paris=result["byExchange"][1]
        self.assertEqual((paris["quality"]["older"],paris["quality"]["unavailable"]),(1,1))
    def test_no_provider_diagnostic_is_unknown_not_zero(self):
        r=build({"companies":[]},{"tickers":[{"ticker":"MISS","exchange":"Other"}]},NOW)
        self.assertIsNone(r["byExchange"][0]["providerOlderSession"])
        self.assertEqual(r["byExchange"][0]["quality"]["unavailable"],1)
        self.assertEqual(r["ageCalendarDays"]["unknownOrFuture"],0)
    def test_age_is_calendar_day_distance_not_http_age(self):
        self.assertEqual(age_bucket({"date":"2026-11-20"},"2026-11-20"),"targetDate")
        self.assertEqual(age_bucket({"date":"2026-11-18"},"2026-11-20"),"twoToThreeDays")
        self.assertEqual(age_bucket({"date":"2026-11-21"},"2026-11-20"),"unknownOrFuture")
        self.assertEqual(age_bucket({"date":"bad"},"2026-11-20"),"unknownOrFuture")
