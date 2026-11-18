import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import context
class PairContextTests(unittest.TestCase):
    def test_excludes_zero_volume_and_missing_close_but_retains_latest_timestamp(self):
        data={"timestamp":[1,2,3,4],"indicators":{"quote":[{"close":[10,11,None,12],"volume":[100,0,100,None]}]}}
        self.assertEqual(context.valid_pair_closes(data),({1:10},4))
    def test_candidates_are_distinct_and_match_metadata(self):
        self.assertEqual(len(context.AB_CANDIDATES),9)
        self.assertEqual(len({x[3] for x in context.AB_CANDIDATES}),9)
        data={"meta":{"symbol":"ELUX-A.ST","currency":"SEK","instrumentType":"EQUITY","longName":"Electrolux AB"}}
        self.assertTrue(context.candidate_match(data,"ELUX-A.ST","SEK","electrolux"))
        self.assertFalse(context.candidate_match(data,"ELUX-B.ST","SEK","electrolux"))
        self.assertFalse(context.candidate_match(data,"ELUX-A.ST","EUR","electrolux"))
    def test_rolling_sufficient_observations(self):
        self.assertIsNone(context.rolling_summary([1]*29,30))
        self.assertEqual(context.rolling_summary([1]*30,30),{"observations":30,"mean":1,"z":None})
    def test_candidate_never_automatically_promoted(self):
        from unittest.mock import patch
        stamps=list(range(1,101))
        def chart(ticker):
            return {"meta":{"symbol":ticker,"currency":"SEK","instrumentType":"EQUITY","longName":"Electrolux AB"},"timestamp":stamps,"indicators":{"quote":[{"close":[100]*100,"volume":[5000]*100}]}}
        checks=[]
        with patch.object(context,"SHARE_CLASSES",[]),patch.object(context,"AB_CANDIDATES",[context.AB_CANDIDATES[0]]),patch.object(context,"_chart",chart):
            self.assertEqual(context.share_classes(checks),[])
        self.assertEqual(checks[0]["status"],"price_checks_passed_identity_review_required")
    def test_latest_bar_health_distinguishes_null_volume_and_zero(self):
        data={"timestamp":[1,2],"indicators":{"quote":[{"close":[10,11],"volume":[100,0]}]}}
        self.assertEqual(context.latest_bar_health(data)["status"],"zero_volume")
        data["indicators"]["quote"][0]["volume"][-1]=None
        self.assertEqual(context.latest_bar_health(data)["status"],"missing_or_invalid_volume")
        data["indicators"]["quote"][0]["close"][-1]=None
        self.assertEqual(context.latest_bar_health(data)["status"],"missing_or_invalid_close")
        self.assertEqual(context.latest_bar_health(None)["status"],"source_unavailable")
    def test_utc_day(self):
        self.assertEqual(context.utc_day(0),"1970-01-01")
    def test_individual_daily_move_requires_exact_adjacent_positive_bars(self):
        from datetime import datetime, timezone
        def stamp(d):
            return int(datetime.fromisoformat(d).replace(tzinfo=timezone.utc).timestamp())
        fri, mon, tue = map(stamp, ("2026-11-13", "2026-11-16", "2026-11-17"))
        data = {"meta": {"symbol": "ATCO-A.ST", "currency": "SEK", "dataGranularity":"1d"},
                "timestamp": [fri,mon,tue], "indicators":{"quote":[{"close":[100,120,108],"volume":[10,20,30]}]}}
        def move(at=tue, ticker="ATCO-A.ST"):
            return context.individual_pair_move(data,ticker,"SEK",at)
        self.assertEqual(move()["changePct"], -10)
        self.assertEqual(move()["previousDate"],"2026-11-16")
        self.assertEqual(move(mon)["changePct"],20)
        self.assertIsNone(move(ticker="ATCO-B.ST"))
        data["indicators"]["quote"][0]["volume"][1]=0
        self.assertIsNone(move())
        data["timestamp"]=[fri,tue]
        data["indicators"]["quote"][0]={"close":[100,108],"volume":[100,100]}
        self.assertIsNone(move())
if __name__=="__main__":unittest.main()
