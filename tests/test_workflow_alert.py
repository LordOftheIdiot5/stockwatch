import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from workflow_alert import message,deliver
REPO="LordOftheIdiot5/stockwatch"
def event(**kw):return {"workflow_run":dict({"id":123,"run_attempt":2,"head_branch":"main","head_repository":{"full_name":REPO},"name":"Scan","event":"push","conclusion":"failure"},**kw)}
class WorkflowAlertTests(unittest.TestCase):
    def test_main_failure_has_run_link(self):
        m=message(event(),REPO);self.assertIn("Scan",m);self.assertIn("/actions/runs/123",m)
    def test_no_secrets_for_untrusted_or_successful_runs(self):
        for e in (event(event="pull_request"),event(head_branch="feature/test"),event(head_repository={"full_name":"other/repo"}),event(conclusion="success"),event(name="Unknown")):
            self.assertIsNone(message(e,REPO))
    def test_retry_and_failure(self):
        calls=[]
        def send(t,c,m):calls.append(m);return len(calls)==2
        self.assertTrue(deliver("test","test","a < b",send,lambda n:None));self.assertEqual(calls,["a &lt; b"]*2)
        with self.assertRaises(RuntimeError):deliver("test","test","x",lambda *a:False,lambda n:None)
