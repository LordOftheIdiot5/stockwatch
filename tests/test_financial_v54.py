import json,sqlite3,sys,tempfile,unittest,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from financial_history import build,filing,identity
class V54(unittest.TestCase):
    def test_revision_and_no_merge(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"repo";(root/"data").mkdir(parents=True);(root/"database").mkdir()
            for p in ("0002_research_assets.sql","0003_financial_history.sql"):shutil.copy(ROOT/"database"/p,root/"database"/p)
            def write(n,d):(root/"data"/n).write_text(json.dumps(d))
            f={"asOf":"2026-09-30","published":"2026-10-22","period":"Q3","currency":"NOK","sourceUrl":"https://example.com/filing","metrics":{"revenue":100,"operatingIncome":20}}
            write("fundamentals.json",{"companies":{"OLD":f}})
            write("issuer-identities.json",{"entities":[{"ticker":"NEW","name":"Example","isin":"NEW-ISIN","previousIsin":"OLD-ISIN","previousTicker":"OLD","historyPolicy":"separate_predecessor_security","corporateActionSource":"https://example.com/action"}]})
            path=Path(tmp)/"warehouse.sqlite"
            first=build(root,path,observed_at="2026-11-01T00:00:00Z")
            self.assertEqual(first["financial_revision"],1);self.assertEqual(first["corporate_action_evidence"],1)
            self.assertEqual(first,build(root,path,observed_at="2026-11-02T00:00:00Z"))
            f["metrics"]["revenue"]=101;write("fundamentals.json",{"companies":{"OLD":f}})
            revised=build(root,path,observed_at="2026-11-03T00:00:00Z");self.assertEqual(revised["financial_revision"],2)
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM financial_revision WHERE previous_fingerprint IS NOT NULL").fetchone()[0],1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM filing_fact WHERE issuer='NEW'").fetchone()[0],0)
            with self.assertRaises(ValueError):build(root,path,[{"subject":"X","filing":f}])
    def test_invalid_facts(self):
        self.assertIsNone(filing("X",{"asOf":"2026-02-30"}))
        self.assertNotIn("evidence",identity({"ticker":"X","name":"X","evidence":"javascript:bad"}))
    def test_repo_path_rejected(self):
        with self.assertRaises(ValueError):build(ROOT,ROOT/"private.sqlite")
