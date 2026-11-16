import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import research_coverage as r
import history_coverage as h
class ResearchCoverageTests(unittest.TestCase):
    def test_mapping_and_outage_history(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/"data").mkdir()
            target={"id":"XOSL:ABC","name":"Example","symbol":"ABC","mic":"XOSL","market":"Norway","isin":None}
            (root/"data/research-targets.json").write_text(json.dumps({"targets":[target]}))
            row={"figi":"BBG000BLNNH6","ticker":"ABC","marketSector":"Equity"}
            def good(j,k):return [{"data":[row]}]
            a=r.build(root,good,"fake")["records"][0]
            self.assertEqual(a["mappingStatus"],"candidate")
            self.assertFalse(a["currentCandidate"]["verified"])
            self.assertEqual(len(a["mappingHistory"]),1)
            self.assertEqual(len(r.build(root,good,"fake")["records"][0]["mappingHistory"]),1)
            def fail(j,k):raise TimeoutError()
            b=r.build(root,fail,"fake")["records"][0]
            self.assertIsNone(b["currentCandidate"])
            self.assertEqual(b["lastCandidate"],a["currentCandidate"])
            self.assertEqual(b["mappingHistory"],a["mappingHistory"])
            self.assertEqual(b["quoteStatus"],"not_connected")
    def test_ambiguity(self):
        t={"symbol":"ABC","mic":"XOSL"}
        a={"figi":"BBG000BLNNH6","ticker":"ABC","marketSector":"Equity"}
        b=dict(a,figi="BBG000BLNNH7")
        self.assertEqual(r.candidate(t,{"data":[a,b]}),("ambiguous",None))
    def test_audit_excludes_unlicensed_historical_price(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);d=root/"data";(d/"history").mkdir(parents=True)
            payload={"ticker":"ABC","bars":[{"date":"2025-01-01","close":1}],"source":"Test"}
            (d/"history/ABC.json").write_text(json.dumps(payload))
            self.assertEqual(h.build(root)["licensedEquityHistory"]["observations"],0)
            payload.update(redistributionPermitted=True,licenseReference="https://example.org/licence",sourceUrl="https://example.org",currency="NOK",adjusted=False)
            (d/"history/ABC.json").write_text(json.dumps(payload))
            self.assertEqual(h.build(root)["licensedEquityHistory"]["observations"],1)
if __name__=="__main__":unittest.main()
