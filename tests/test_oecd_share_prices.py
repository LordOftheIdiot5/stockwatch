import sys,unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from oecd_share_prices import inspect
HEAD="REF_AREA,FREQ,MEASURE,UNIT_MEASURE,ACTIVITY,ADJUSTMENT,TRANSFORMATION,TIME_HORIZON,METHODOLOGY,TIME_PERIOD,OBS_VALUE,OBS_STATUS,UNIT_MULT,BASE_PER"+chr(10)
ROW="JPN,M,SHARE,IX,_Z,_Z,_Z,_Z,N,2026-10,150.0,A,0,2015"+chr(10)
class OECDTests(unittest.TestCase):
    def test_metadata_only(self):
        x=inspect(HEAD+ROW+ROW.replace("JPN","NOR"),date(2026,11,20))
        self.assertEqual(x["referenceAreas"],2);self.assertEqual(x["publishedValues"],0)
        self.assertNotIn("150.0",str(x))
    def test_conflict_and_wrong_base(self):
        with self.assertRaises(ValueError):inspect(HEAD+ROW+ROW.replace("150.0","151.0"),date(2026,11,20))
        with self.assertRaises(ValueError):inspect(HEAD+ROW.replace("2015","2020"),date(2026,11,20))
