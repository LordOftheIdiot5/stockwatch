import csv,io,unittest,sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from delayed_exchange import REQUIRED
from euronext_condition_evidence import FIELDS
from euronext_price_stage import stage,inspect,ELIGIBLE,EXCLUDED

PAIR=("NO0010096985","XOSL")
FIELDS_ALL=sorted(REQUIRED)+list(FIELDS)
A=("1","-","-","-","-","ALGO","-","-","MONE","")
B=("3","-","-","RFPT","-","-","-","-","MONE","")
assert A in ELIGIBLE and B in EXCLUDED
def trade(uid,at,price,flags=A,currency="NOK"):
    x=dict.fromkeys(FIELDS_ALL,"-")
    x.update(MifidInstrumentID=PAIR[0],Venue=PAIR[1],TradeUniqueIdentifier=uid,
        TradingDateTime=at,PublicationDateTime=at,
        MifidPrice=str(price),MifidQuantity="25",MifidCurrency=currency)
    x.update(dict(zip(FIELDS,flags)))
    return x
def ziprows(records,fields=FIELDS_ALL):
    buf=io.BytesIO();body=io.StringIO();body.write("Copyright Euronext\n")
    writer=csv.DictWriter(body,fieldnames=fields,delimiter=";")
    writer.writeheader();writer.writerows(records)
    with zipfile.ZipFile(buf,"w") as z:z.writestr("report.csv",body.getvalue())
    return buf.getvalue()
class Tests(unittest.TestCase):
    def test_true_last_eligible_trade_not_later_off_book_price(self):
        rows=[trade("1","2026-11-19T15:00:00Z","100"),
              trade("2","2026-11-19T15:20:00Z","102"),
              trade("3","2026-11-19T15:50:00Z","999",B)]
        data,stats=stage(ziprows(rows),{PAIR:["ref:XOSL:EQNR"]})
        self.assertEqual(len(data),1)
        self.assertEqual(data[0]["lastTradePrice"],"102")
        self.assertEqual(data[0]["date"],"2026-11-19")
        self.assertEqual(data[0]["currency"],"NOK")
        self.assertFalse(data[0]["officialClose"])
        self.assertFalse(data[0]["publicPublicationAllowed"])
        self.assertEqual(data[0]["observedEligibleTrades"],2)
        self.assertEqual(stats["counts"]["derivedSessions"],1)
    def test_unknown_condition_blocks_entire_session(self):
        bad=list(A);bad[2]="CANC"
        data,stats=stage(ziprows([trade("1","2026-11-19T15:00:00Z","100"),
                                  trade("2","2026-11-19T15:30:00Z","101",tuple(bad))]),{PAIR:["ID"]})
        self.assertEqual(data,[])
        self.assertEqual(stats["quarantined"]["blocked"],1)
    def test_conflicting_trade_id_blocks(self):
        rows=[trade("1","2026-11-19T15:00:00Z","100"),
              trade("1","2026-11-19T15:00:00Z","900")]
        out,stats=stage(ziprows(rows),{PAIR:["ID"]})
        self.assertFalse(out);self.assertEqual(stats["counts"]["conflictingTradeIds"],1)
    def test_exact_duplicate_id_is_safe_but_not_double_counted(self):
        a=trade("1","2026-11-19T15:00:00Z","100")
        out,stats=stage(ziprows([a,a]),{PAIR:["ID"]})
        self.assertEqual(out[0]["observedEligibleTrades"],1)
    def test_mixed_currency_or_same_timestamp_conflict_blocks(self):
        rows=[trade("1","2026-11-19T15:00:00Z","100"),
              trade("2","2026-11-19T15:01:00Z","101",currency="EUR")]
        out,stats=stage(ziprows(rows),{PAIR:["ID"]})
        self.assertFalse(out);self.assertEqual(stats["quarantined"]["mixedCurrency"],1)
        rows=[trade("1","2026-11-19T15:00:00Z","100"),
              trade("2","2026-11-19T15:00:00Z","101")]
        out,stats=stage(ziprows(rows),{PAIR:["ID"]})
        self.assertFalse(out);self.assertEqual(stats["quarantined"]["ambiguousLastTrade"],1)
    def test_missing_fields_are_refused_not_assumed(self):
        fields=[f for f in FIELDS_ALL if f!="MmtMarketMechanism"]
        with self.assertRaisesRegex(ValueError,"mandatory condition"):stage(ziprows([],fields),{PAIR:["ID"]})
    def test_ambiguous_listing_rejected(self):
        with self.assertRaisesRegex(ValueError,"ambiguous"):stage(ziprows([]),{PAIR:["A","B"]})
    def test_no_raw_or_price_data_leaked_from_summary(self):
        from unittest.mock import patch
        from euronext_price_stage import inspect
        queue={"queues":{"euronext":{"records":[{"id":"ref:XOSL:EQNR","mic":"XOSL","isin":PAIR[0],"identityStatus":"isin_and_mic"}]}}}
        def fetch(url):return ziprows([trade("1","2026-11-19T15:00:00Z","123.45")])
        with patch("builtins.print") as echo:
            result=inspect(queue,[],fetch=fetch)
        self.assertEqual(result["ephemeralDatedObservations"],1)
        self.assertEqual(result["publishedPrices"],0)
        self.assertFalse(result["internalArchiveWritten"])
        self.assertNotIn("123.45",str(echo.call_args))
        self.assertNotIn(PAIR[0],str(echo.call_args))
if __name__=="__main__":unittest.main()
