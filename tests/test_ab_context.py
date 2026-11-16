import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import context
class PairContextTests(unittest.TestCase):
    def test_excludes_zero_volume_and_missing_close_but_retains_latest_timestamp(self):
        data={"timestamp":[1,2,3,4],"indicators":{"quote":[{"close":[10,11,None,12],"volume":[100,0,100,None]}]}}
        self.assertEqual(context.valid_pair_closes(data),({1:10},4))
    def test_utc_day(self):
        self.assertEqual(context.utc_day(0),"1970-01-01")
if __name__=="__main__":unittest.main()
