import json,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from esma_identity_history import build,make_snapshot
PAIR=("NO0005052605","XOSL");LEI="5493001KJTIIGC8Y1R12"
FILE={"name":"FULINS_E_20261114_01of01.zip"}
M={"latestEquityFullSet":{"date":"2026-11-14","complete":True,"expectedParts":1,"files":[FILE]},"subsequentDeltaAndCancellationSets":[{"type":"FULCAN","date":"2026-11-14","complete":True}]}
PARTS=[{**FILE,"rows":10,"sha256":"a"*64}]
MATCH={PAIR:{(LEI,"ESVUFR","NOK")}}
class ESMAHistory(unittest.TestCase):
    def test_exact_pairs_and_no_current_claim(self):
        s=make_snapshot(M,{PAIR:{"NHY.OL"},(PAIR[0],"XSTO"):{"other"}},MATCH,PARTS,{PAIR[0]:{LEI}},{"sourceDate":"2026-11-19"})
        self.assertEqual(s["matchedPairs"],1);self.assertEqual(s["unmatchedPairs"],1)
        self.assertEqual(s["comparisonCounts"],{"agree":1,"not_comparable":1})
        self.assertFalse(s["currentStateEstablished"])
    def test_incomplete_parts_fail(self):
        with self.assertRaises(ValueError):make_snapshot(M,{PAIR:{"NHY.OL"}},MATCH,[],{}, {})
    def test_conflict_is_review_not_merge(self):
        s=make_snapshot(M,{PAIR:{"NHY.OL"}},MATCH,PARTS,{PAIR[0]:{"other"}},{})
        self.assertEqual(s["records"][0]["gleifComparison"],"review")
    def test_idempotence_and_outage_retention(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"data").mkdir();(root/"data/listing-coverage-v1.json").write_text(json.dumps({"records":[{"id":"NHY.OL","isin":PAIR[0],"mic":PAIR[1]}]}))
            args={"discover":lambda:M,"fetch":lambda m,e:(MATCH,PARTS)}
            a=build(root,datetime(2026,11,19,tzinfo=timezone.utc),**args)
            b=build(root,datetime(2026,11,20,tzinfo=timezone.utc),**args)
            self.assertEqual(a["snapshot"],b["snapshot"]);self.assertTrue((root/a["snapshot"]).is_file())
            def fail():raise TimeoutError()
            with self.assertRaises(TimeoutError):build(root,datetime(2026,11,21,tzinfo=timezone.utc),discover=fail)
            idx=json.loads((root/"data/esma-equity-history/index.json").read_text())
            self.assertEqual(idx["snapshot"],a["snapshot"]);self.assertEqual(idx["status"],"retained_after_error")
