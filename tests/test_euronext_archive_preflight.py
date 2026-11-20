import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from euronext_archive_preflight import check,main

class Tests(unittest.TestCase):
    def test_readonly_default_requires_no_approval(self):
        self.assertEqual(check("false","","","refs/pull/165/merge"),"ephemeral_only")
    def test_approved_requires_both_explicit_flags_on_main(self):
        self.assertEqual(check("true","true","true","refs/heads/main"),"approved_private_r2")
    def test_manual_input_does_not_override_r2_review(self):
        with self.assertRaisesRegex(ValueError,"STOCKWATCH_R2_RETENTION_APPROVED"):
            check("true","false","true","refs/heads/main")
    def test_manual_input_does_not_override_derived_review(self):
        with self.assertRaisesRegex(ValueError,"STOCKWATCH_EURONEXT_STAGE_RETENTION_APPROVED"):
            check("true","true","false","refs/heads/main")
    def test_reject_other_branches(self):
        with self.assertRaisesRegex(ValueError,"main branch"):
            check("true","true","true","refs/heads/preview")
    def test_invalid_approval_input(self):
        with self.assertRaisesRegex(ValueError,"Invalid"):
            check("yes","true","true","refs/heads/main")
    def test_user_facing_failure_has_no_secret_values(self):
        env={"RETAIN":"true","STOCKWATCH_R2_RETENTION_APPROVED":"false",
             "STOCKWATCH_EURONEXT_STAGE_RETENTION_APPROVED":"true",
             "STOCKWATCH_R2_SECRET_ACCESS_KEY":"very_secret_token",
             "GITHUB_REF":"refs/heads/main"}
        from io import StringIO
        from contextlib import redirect_stdout
        out=StringIO()
        with patch.dict("os.environ",env,clear=True),redirect_stdout(out):
            self.assertEqual(main(),1)
        self.assertIn("STOCKWATCH_R2_RETENTION_APPROVED",out.getvalue())
        self.assertNotIn("very_secret_token",out.getvalue())
if __name__=="__main__":unittest.main()
