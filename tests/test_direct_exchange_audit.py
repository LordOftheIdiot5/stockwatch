import unittest,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from direct_exchange_audit import reference,audit,isin_ok,candidate_keys,crosscheck,firds_check
class DirectExchangeTests(unittest.TestCase):
 def test_descriptor_and_identity_no_quote_fields(self):
  raw=b"environment=PROD,created=2026-11-16,time=08:00Z\nisin,mic,currency,company_name,live,asset_class,bats_name,reference_price,bats_prev_close\nNO0010096985,XOSL,NOK,Equinor,t,EQTY,EQNRo,555,333\n"
  rows,summary=reference(raw,datetime(2026,11,17,tzinfo=timezone.utc))
  self.assertEqual(len(rows),1);self.assertNotIn("555",str(rows));self.assertNotIn("333",str(rows))
  self.assertTrue(isin_ok("NO0010096985"));self.assertFalse(isin_ok("NO0010096986"))
  x=audit([{"ticker":"EQNR.OL","name":"Equinor"},{"ticker":"X.ST","name":"Equinor"}],[{"ticker":"EQNR.OL","isin":"NO0010096985","evidence":"fixture"}],rows)
  self.assertEqual(x["counts"],{"existing_isin_overlap":1,"unresolved":1});self.assertFalse(x["priceCoverageVerified"])
 def test_name_candidate_never_verified(self):
  x=audit([{"ticker":"X.OL","name":"Example AB"}],[],{("NO0010096985","XOSL","NOK","example ab","EXo")})
  self.assertEqual(x["counts"],{"unique_name_candidate":1})
 def test_reject_nonproduction(self):
  with self.assertRaises(ValueError):reference(b"environment=CERT,created=2026-11-16\n",datetime(2026,11,17,tzinfo=timezone.utc))

 def test_symbol_candidate_preserves_class(self):
  watch=[{"ticker":"ERIC-A.ST","name":"Ericsson"},{"ticker":"ERIC-B.ST","name":"Ericsson"}]
  figis=[{"ticker":x["ticker"],"name":"Different full name","match":"single_instrument_same_mic_candidate","figi":"fixture"+str(i)} for i,x in enumerate(watch)]
  items={("SE0000108649","XSTO","SEK","ericsson a","ERICAs"),("SE0000108656","XSTO","SEK","ericsson b","ERICBs")}
  keys,rows,counts=candidate_keys(watch,figis,items)
  self.assertEqual(len(keys),2);self.assertEqual(counts["candidate_found"],2)
  self.assertEqual(crosscheck(watch,figis,items,"")["status"],"missing_existing_openfigi_key")

 def test_firds_exact_reference_not_price_approval(self):
  import json
  watch=[{"ticker":"EQNR.OL","exchange":"Oslo"}]
  matches=[{"listingId":"EQNR.OL","isin":"NO0010096985","mic":"XOSL"}]
  row={"isin":"NO0010096985","mic":"XOSL","gnr_cfi_code":"ESVUFR","gnr_notional_curr_code":"NOK"}
  def read(u):
   self.assertIn("latest_received_flag%3A1",u)
   return json.dumps({"response":{"numFound":1,"docs":[row]}}).encode()
  result=firds_check(matches,watch,read)
  self.assertEqual(result["counts"],{"exact_reference_match":1})
  self.assertFalse(result["currentTradingStatusVerified"])
  self.assertFalse(result["priceCoverageVerified"])
  with self.assertRaises(ValueError):firds_check(matches,watch,lambda u:b'{"response":{"numFound":2,"docs":[]}}')
