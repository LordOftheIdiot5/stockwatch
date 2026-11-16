import csv,io,sys,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import exchange_capacity as a
import delayed_exchange as ex

def fixture():
    fields=sorted(ex.REQUIRED)
    buf=io.StringIO()
    w=csv.DictWriter(buf,fieldnames=fields);w.writeheader()
    record=dict(TradingDateTime="2026-11-16T09:00:00Z",PublicationDateTime="2026-11-16T09:15:00Z",MifidInstrumentID="NO0010096985",MifidPrice="100",MifidQuantity="3",MifidCurrency="NOK",Venue="XOSL",TradeUniqueIdentifier="a")
    w.writerow(record);w.writerow(record)
    w.writerow({**record,"MifidInstrumentID":"invalid","TradingDateTime":"bad"})
    buf.write("bad,row\n")
    zbuf=io.BytesIO()
    with zipfile.ZipFile(zbuf,"w") as z:z.writestr("trade.csv",buf.getvalue())
    return zbuf.getvalue()

class CapacityTests(unittest.TestCase):
    def test_counts_are_not_unique_trades(self):
        r=a.measure(fixture())
        self.assertEqual(r["reportRows"],4)
        self.assertEqual(r["malformedRows"],1)
        self.assertEqual(r["invalidIdentityRows"],1)
        self.assertEqual(r["invalidTimestampRows"],1)
        self.assertEqual(r["distinctValidISINs"],1)
        self.assertEqual(r["tradeUTCDateMin"],"2026-11-16")
        self.assertFalse(r["uniqueExecutedTradesVerified"])
        self.assertFalse(r["rawReportStored"])
        self.assertNotIn("prices",r)
    def test_market_isolation(self):
        def fetch(url):return b"html" if url.endswith("/OSL") else fixture()
        self.assertEqual([r["status"] for r in a.audit(["OSL","PAR"],fetch)],["unavailable","measured"])
    def test_rate_limit_stops(self):
        def fetch(url):raise ex.HTTPError(url,429,"",{},None)
        self.assertEqual(len(a.audit(["OSL","PAR"],fetch)),1)
    def test_reject_bad_zip(self):
        with self.assertRaises(zipfile.BadZipFile):a.measure(b"html")
if __name__=="__main__":unittest.main()
