import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from us_figi_bridge import classify,jobs
SEED={"id":"XNAS:NVDA","cik":"0001045810","mic":"XNAS","symbol":"NVDA","identityStatus":"sec_ticker_exchange_association"}
ROW={"ticker":"NVDA","marketSector":"Equity","securityType2":"Common Stock","figi":"BBG000BBJQV0","compositeFIGI":"BBG000BBJQV0","shareClassFIGI":"BBG001S5S399"}
class BridgeTests(unittest.TestCase):
    def test_exact_common_stock(self):
        self.assertEqual(jobs([SEED])[0][1]["micCode"],"XNAS")
        x=classify(SEED,{"data":[ROW]})
        self.assertEqual(x["status"],"candidate")
        self.assertFalse(x["verified"])
    def test_reject_wrong_symbol_and_preferred(self):
        self.assertEqual(classify(SEED,{"data":[dict(ROW,ticker="OTHER"),dict(ROW,securityType2="Preferred Stock")]})["status"],"unmatched")
    def test_error_not_unmatched(self):
        with self.assertRaises(ValueError):classify(SEED,{"error":"bad request"})
