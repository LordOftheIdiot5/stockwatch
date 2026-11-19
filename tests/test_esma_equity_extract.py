import io,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from esma_equity_extract import extract,NS
def xml(mic="XOSL",lei="5493001KJTIIGC8Y1R12"):
    return io.BytesIO(f'<Document xmlns="{NS[1:-1]}"><FinInstrmRptgRefDataRpt><RefData><FinInstrmGnlAttrbts><Id>NO0005052605</Id><ClssfctnTp>ESVUFR</ClssfctnTp><NtnlCcy>NOK</NtnlCcy></FinInstrmGnlAttrbts><Issr>{lei}</Issr><TradgVnRltdAttrbts><Id>{mic}</Id></TradgVnRltdAttrbts></RefData></FinInstrmRptgRefDataRpt></Document>'.encode())
class ExtractionTests(unittest.TestCase):
    def test_exact_pair(self):
        key=("NO0005052605","XOSL")
        count,matches=extract(xml(),{key})
        self.assertEqual(count,1)
        self.assertEqual(matches[key],{("5493001KJTIIGC8Y1R12","ESVUFR","NOK")})
        self.assertFalse(extract(xml("XSTO"),{key})[1])
    def test_bad_lei(self):
        with self.assertRaises(ValueError):extract(xml(lei="INVALID"),{("NO0005052605","XOSL")})
    def test_wrong_schema_or_empty(self):
        with self.assertRaises(ValueError):extract(io.BytesIO(b"<Document/>"),set())
