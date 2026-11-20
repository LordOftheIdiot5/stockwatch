import csv,io,sys,unittest,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from euronext_condition_evidence import inspect,FIELDS
from delayed_exchange import REQUIRED
KEY=("NO0010096985","XOSL")
def fixture(flags):
    b=io.BytesIO();s=io.StringIO();h=sorted(REQUIRED)+list(FIELDS);w=csv.DictWriter(s,fieldnames=h,delimiter=";");w.writeheader()
    for i,flag in enumerate(flags):
        row=dict.fromkeys(h,"-");row.update(MifidInstrumentID=KEY[0],Venue=KEY[1],TradeUniqueIdentifier=str(i),MmtModificationIndicator=flag)
        w.writerow(row)
    with zipfile.ZipFile(b,"w") as z:z.writestr("data.csv",s.getvalue())
    return b.getvalue()
class Tests(unittest.TestCase):
    def test_counts_and_no_price(self):
        r=inspect(fixture(["-","AMND","CANC"]),{KEY:["EQNR"]})
        self.assertEqual(r["counts"]["revisionReports"],2);self.assertEqual(r["affectedExactPairs"]["revision"],1);self.assertFalse(r["pricePublished"])
    def test_exact_match(self):
        r=inspect(fixture(["-"]),{("NO0010096985","XPAR"):["OTHER"]})
        self.assertEqual(r["counts"]["scanned"],1);self.assertEqual(r["counts"].get("matched",0),0)
