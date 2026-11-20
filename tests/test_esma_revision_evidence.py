import io,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from esma_revision_evidence import extract,NS
PAIR=("NO0005052605","XOSL")
LEI="5493001KJTIIGC8Y1R12"
def xml(action="ModfdRcrd",mic="XOSL",publication="2026-11-19",termination=""):
    inner=f'<FinInstrmGnlAttrbts><Id>{PAIR[0]}</Id><ClssfctnTp>ESVUFR</ClssfctnTp><NtnlCcy>NOK</NtnlCcy></FinInstrmGnlAttrbts><Issr>{LEI}</Issr><TradgVnRltdAttrbts><Id>{mic}</Id><FrstTradDt>2020-01-02T08:00:00Z</FrstTradDt>{termination}</TradgVnRltdAttrbts><TechAttrbts><PblctnPrd><FrDt>{publication}</FrDt></PblctnPrd></TechAttrbts>'
    return io.BytesIO(f'<Document xmlns="{NS[1:-1]}"><FinInstrmRptgRefDataDltaRpt><FinInstrm><{action}>{inner}</{action}></FinInstrm></FinInstrmRptgRefDataDltaRpt></Document>'.encode())
class RevisionTests(unittest.TestCase):
    def test_exact_scope_and_dates(self):
        counts,rows=extract(xml(),{PAIR:{"NHY.OL"}})
        self.assertEqual(counts,{"ModfdRcrd":1});self.assertEqual(rows[0]["publicationFrom"],"2026-11-19")
        self.assertEqual(rows[0]["firstTradeAt"],"2020-01-02T08:00:00Z")
        self.assertEqual(extract(xml(mic="XSTO"),{PAIR:{"NHY.OL"}})[1],[])
    def test_termination_is_preserved_not_deletion(self):
        _,rows=extract(xml("TermntdRcrd",termination="<TermntnDt>2026-11-18T16:00:00Z</TermntnDt>"),{PAIR:{"NHY.OL"}})
        self.assertEqual(rows[0]["action"],"TermntdRcrd");self.assertEqual(rows[0]["terminationAt"],"2026-11-18T16:00:00Z")
    def test_unknown_cancellation_fails_closed(self):
        x=io.BytesIO(f'<Document xmlns="{NS[1:-1]}"><FinInstrmRptgRefDataDltaRpt><FinInstrm><CancRcrd><Id>test</Id></CancRcrd></FinInstrm></FinInstrmRptgRefDataDltaRpt></Document>'.encode())
        with self.assertRaisesRegex(ValueError,"cancellation schema"):extract(x,{PAIR:{"NHY.OL"}})
    def test_missing_validity_date_rejected(self):
        with self.assertRaises(ValueError):extract(xml(publication=""),{PAIR:{"NHY.OL"}})
