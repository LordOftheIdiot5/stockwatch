import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import instrument_directory as d
class DirectoryTests(unittest.TestCase):
    def row(self):
        return {"figi":"BBG000BLNNH6","name":"Example","ticker":"A","marketSector":"Equity","securityType":"Common Stock"}
    def test_reference_only(self):
        x=d.normalize(self.row(),"XOSL")
        self.assertEqual(x["quoteStatus"],"not_connected")
        self.assertNotIn("close",x)
        self.assertIsNone(d.normalize(dict(self.row(),securityType="Option"),"XOSL"))
    def test_pagination_and_dedup(self):
        calls=[]
        def fetch(p,k):
            calls.append(p)
            return {"data":[self.row()],"next":"cursor"} if len(calls)==1 else {"data":[self.row()]}
        rows,complete=d.collect("XOSL","test",fetch,lambda _:None)
        self.assertTrue(complete);self.assertEqual(len(rows),1)
        self.assertEqual(calls[1]["start"],"cursor")
    def test_failure_preserves_previous(self):
        with tempfile.TemporaryDirectory() as t, patch.dict("os.environ",{"STOCKWATCH_OPENFIGI_KEY":"fake"}):
            root=Path(t);(root/"data").mkdir()
            (root/d.OUT).write_text(json.dumps({"records":[d.normalize(self.row(),"XOSL")]}))
            def fail(*a): raise TimeoutError()
            result=d.build(root,fail,lambda _:None)
            self.assertEqual(len(result["records"]),1)
            self.assertEqual(result["venues"]["XOSL"]["status"],"error")
if __name__=="__main__":unittest.main()
