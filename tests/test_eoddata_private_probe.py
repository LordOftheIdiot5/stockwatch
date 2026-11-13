"""Key non-disclosure and no-public-output regression checks."""
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from eoddata_private_probe import exchange_listing
from urllib.error import HTTPError

class ProbeTests(unittest.TestCase):
 def test_uses_eoddata_endpoint_without_printing_key(self):
  secret='PRIVATE_TEST_KEY_NOT_REAL'
  class FakeResponse:
   status=200
   def __enter__(self):return self
   def __exit__(self,*_):pass
   def read(self,limit):return b'[{"code":"OSL"}]'
  def opener(req,timeout):
   self.assertEqual(timeout,15)
   self.assertIn('/Exchange/List?apiKey=',req.full_url)
   self.assertIn(secret,req.full_url)
   return FakeResponse()
  self.assertEqual(len(exchange_listing(secret,opener)),1)
 def test_http_error_never_prints_key(self):
  secret='ANOTHER_PRIVATE_TEST_KEY'
  def fail(req,timeout):raise HTTPError(req.full_url,403,'Denied',{},None)
  with self.assertRaises(RuntimeError) as err:exchange_listing(secret,fail)
  self.assertIn('HTTP 403',str(err.exception))
  self.assertNotIn(secret,str(err.exception))
 def test_missing_key_fails_closed(self):
  with self.assertRaisesRegex(ValueError,'Missing EODDATA_API_KEY'):exchange_listing('')

if __name__=='__main__':unittest.main()
