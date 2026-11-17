import sys,unittest
from pathlib import Path
from datetime import datetime,timezone
from copy import deepcopy
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from daily_recovery import missing_target,merge_exact_day,exact_day_url,recovery_validation
class RecoveryTests(unittest.TestCase):
 def test_exact_session_recovery_and_rejections(self):
  now=datetime(2026,11,17,1,tzinfo=timezone.utc)
  ts=int(datetime(2026,11,16,8,tzinfo=timezone.utc).timestamp())
  meta={"symbol":"A.ST","currency":"SEK","exchangeName":"STO","exchangeTimezoneName":"Europe/Stockholm","instrumentType":"EQUITY","dataGranularity":"1d"}
  old={"meta":meta,"timestamp":[ts-86400*3,ts],"indicators":{"quote":[{k:[10,None] for k in ("open","high","low","close","volume")}]}}
  new={"meta":dict(meta),"timestamp":[ts],"indicators":{"quote":[{"open":[10],"high":[12],"low":[9],"close":[11],"volume":[1000]}]}}
  self.assertIsNotNone(missing_target(old,now))
  out=merge_exact_day(old,new,"A.ST",now)
  self.assertEqual(out["indicators"]["quote"][0]["close"],[10,11])
  self.assertEqual(old["indicators"]["quote"][0]["close"],[10,None])
  for field,value in (("symbol","B.ST"),("currency","EUR"),("exchangeName","OTHER")):
   x=deepcopy(new);x["meta"][field]=value
   self.assertIsNone(merge_exact_day(old,x,"A.ST",now))
  x=deepcopy(new);x["timestamp"]=[ts+1]
  self.assertEqual(recovery_validation(old,x,"A.ST",now),"accepted_same_local_session")
  self.assertEqual(merge_exact_day(old,x,"A.ST",now)["timestamp"],old["timestamp"])
  x["timestamp"]=[ts+86400]
  self.assertEqual(recovery_validation(old,x,"A.ST",now),"session_date_mismatch")
  self.assertIsNone(merge_exact_day(old,x,"A.ST",now))
  x=deepcopy(new);del x["meta"]["exchangeName"]
  self.assertEqual(recovery_validation(old,x,"A.ST",now),"missing_metadata_exchangeName")
  x=deepcopy(new);x["indicators"]["quote"][0]["volume"]=[0]
  self.assertIsNone(merge_exact_day(old,x,"A.ST",now))
  self.assertIsNone(missing_target(old,datetime(2026,11,18,1,tzinfo=timezone.utc)))
  target=missing_target(old,now)
  self.assertIn("includePrePost=false",exact_day_url("A.ST",target[0],target[1]))
