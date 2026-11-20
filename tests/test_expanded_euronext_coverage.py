import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from expanded_euronext_coverage import joined
A={"id":"A","mic":"XOSL","isin":"NO0010096985","identityStatus":"isin_and_mic"}
B={"id":"B","mic":"XOSL","figi":"BBG000BXRMY9","identityStatus":"figi_and_mic"}
C={"listingId":"B","mic":"XOSL","isin":"NO0005052605","figi":B["figi"],"status":"exact_candidate_join","reviewRequired":True,"pricePublicationAllowed":False}
Q={"queues":{"euronext":{"records":[A,B]}}}
class Tests(unittest.TestCase):
    def test_new_exact_candidate(self):
        groups,total,added=joined(Q,[C])
        self.assertEqual((total,added,len(groups["OSL"])),(2,1,2))
    def test_conflicts(self):
        for bad in ({**C,"isin":A["isin"]},{**C,"figi":"WRONG"},{**C,"pricePublicationAllowed":True}):
            with self.assertRaises(ValueError):joined(Q,[bad])
    def test_duplicates(self):
        with self.assertRaises(ValueError):joined(Q,[C,C])
