import csv,io,sys,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from euronext_price_coverage import parse,targets
I="NO0010096985";M="XOSL";KEY=(I,M)
FIELDS=["TradingDateTime","PublicationDateTime","MifidInstrumentID","MifidPrice","MifidQuantity","MifidCurrency","Venue","TradeUniqueIdentifier"]
ROW=["2026-11-19T15:20:00Z","2026-11-19T15:20:01Z",I,"250","10","NOK",M,"id1"]
def ziprows(rows):
    out=io.BytesIO();f=io.StringIO();f.write("Copyright notice\n");w=csv.writer(f,delimiter=";");w.writerow(FIELDS);w.writerows(rows)
    with zipfile.ZipFile(out,"w") as z:z.writestr("trades.csv",f.getvalue())
    return out.getvalue()
class Tests(unittest.TestCase):
    def test_exact_identity_counts_only(self):
        r=parse(ziprows([ROW,[*ROW[:6],"XPAR","id2"]]),{KEY:["EQNR"]})
        self.assertEqual(r["matchedListings"],1);self.assertEqual(r["counts"]["sourceRows"],2);self.assertFalse(r["officialCloseEstablished"]);self.assertEqual(r["pricesPublished"],0)
    def test_duplicate_and_invalid_trade(self):
        r=parse(ziprows([ROW,ROW,[*ROW[:3],"NaN",*ROW[4:]]]),{KEY:["EQNR"]})
        self.assertEqual(r["counts"]["repeatedTradeId"],1);self.assertEqual(r["counts"]["invalidMatchedRows"],1)
    def test_no_exact_match(self):
        r=parse(ziprows([ROW]),{("NO0010096985","XPAR"):["OTHER"]})
        self.assertEqual(r["matchedListings"],0)
    def test_targets_reject_unconfirmed_identity(self):
        q={"queues":{"euronext":{"records":[{"id":"EQNR","isin":I,"mic":M,"identityStatus":"isin_and_mic"},{"id":"OTHER","isin":I,"mic":M,"identityStatus":"figi_and_mic"}]}}}
        g,n=targets(q);self.assertEqual(n,2);self.assertEqual(g["OSL"][KEY],["EQNR"])
