import unittest,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from price_freshness import comparison_date,price_quality,coverage,current_alerts
class PriceFreshnessTests(unittest.TestCase):
 def test_completed_session_and_weekend(self):
  self.assertEqual(comparison_date(datetime(2026,11,16,21,tzinfo=timezone.utc)),"2026-11-13")
  self.assertEqual(comparison_date(datetime(2026,11,16,22,tzinfo=timezone.utc)),"2026-11-16")
  self.assertEqual(comparison_date(datetime(2026,11,15,23,tzinfo=timezone.utc)),"2026-11-13")
 def test_health_and_alerts(self):
  now=datetime(2026,11,17,1,tzinfo=timezone.utc)
  row={"ticker":"X","date":"2026-11-13","close":10,"changePct":0,"volume":100}
  alert={"kind":"price","fresh":True,"ticker":"X","key":"px:X:2026-11-13"}
  news={"kind":"news","fresh":True}
  s={"companies":[row],"alerts":[alert,news]}
  h=coverage(s,{"tickers":[{"ticker":"X"},{"ticker":"Y"}]},{},now)
  self.assertEqual(h["equities"]["older"],1)
  self.assertEqual(h["equities"]["unavailable"],1)
  self.assertEqual(h["status"],"degraded")
  self.assertEqual(current_alerts(s,now),[news])
  good={**row,"date":"2026-11-16"}
  self.assertEqual(price_quality(good,"2026-11-16"),"comparable")
  self.assertEqual(price_quality({**good,"volume":0},"2026-11-16"),"no_volume")
  s["companies"]=[{**good,"ticker":str(i)} for i in range(10)]
  a={**alert,"ticker":"0","key":"px:0:2026-11-16"}
  s["alerts"]=[a,news]
  self.assertEqual(current_alerts(s,now),[a,news])
