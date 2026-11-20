import io,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from listing_identity_batch import eligible,extract,match,NS
KEY=("NO0010096985","XOSL")
FIGI="BBG000BXRMY9"
LEI="5493001KJTIIGC8Y1R12"
def xml(venue="XOSL",cfi="ESVUFR"):
    ns=NS[1:-1]
    return io.BytesIO(f'<Document xmlns="{ns}"><RefData><FinInstrmGnlAttrbts><Id>{KEY[0]}</Id><ClssfctnTp>{cfi}</ClssfctnTp><NtnlCcy>NOK</NtnlCcy></FinInstrmGnlAttrbts><Issr>{LEI}</Issr><TradgVnRltdAttrbts><Id>{venue}</Id></TradgVnRltdAttrbts></RefData></Document>'.encode())
class Tests(unittest.TestCase):
    def test_exact_scope(self):
        n,k=extract(xml(),{"XOSL"})
        self.assertEqual(n,1);self.assertEqual(k[KEY],{(LEI,"ESVUFR","NOK")})
        self.assertFalse(extract(xml(),{"XSTO"})[1])
        self.assertFalse(extract(xml(cfi="EPVUFR"),{"XOSL"})[1])
    def test_queue_only_missing_exact_figi(self):
        q={"queues":{"test":{"records":[{"id":"A","mic":"XOSL","figi":FIGI},{"id":"B","mic":"XOSL","figi":FIGI,"isin":KEY[0]},{"id":"C","mic":"XSTO","figi":FIGI},{"id":"D","mic":"XOSL"}]}}}
        self.assertEqual(eligible(q,"euronext"),{"A":(FIGI,"XOSL")})
    def test_candidate_evidence_not_price(self):
        data={KEY:{(LEI,"ESVUFR","NOK")}}
        def mapper(k,rows,key):
            self.assertEqual(k,[KEY]);return [{"listingId":"A","isin":KEY[0],"mic":"XOSL","figi":FIGI,"reviewRequired":True,"pricePublicationAllowed":False}],{}
        r,_=match(data,[],{"A":(FIGI,"XOSL")},"key",mapper)
        self.assertEqual(r[0]["lei"],LEI);self.assertFalse(r[0]["pricePublicationAllowed"])
    def test_ambiguous_source_pair_withheld(self):
        data={KEY:{(LEI,"ESVUFR","NOK"),(LEI,"ESVUFR","EUR")}}
        def mapper(k,rows,key):
            self.assertEqual(k,[]);return [],{}
        self.assertEqual(match(data,[],{"A":(FIGI,"XOSL")},"key",mapper)[0],[])
    def test_wrong_identity_rejected(self):
        def mapper(*args):return [{"listingId":"A","isin":KEY[0],"mic":"XOSL","figi":"OTHER"}],{}
        with self.assertRaises(ValueError):match({KEY:{(LEI,"ESVUFR","NOK")}},[],{"A":(FIGI,"XOSL")},"key",mapper)
