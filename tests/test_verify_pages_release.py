import importlib.util,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location("verify_pages_release",ROOT/"scripts/verify_pages_release.py")
m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_bounded_eventual_consistency(self):
        with tempfile.TemporaryDirectory() as d:
            prior=m.ROOT
            try:
                m.ROOT=Path(d)
                for p in m.PATHS:(m.ROOT/p).write_bytes(("<html>"+p+"</html>").encode())
                attempts=[]
                def fetch(p,n):
                    attempts.append((p,n))
                    return b"stale" if n==1 else (m.ROOT/p).read_bytes()
                result=m.check(attempts=2,interval=0,fetch=fetch)
                self.assertTrue(all(x["match"] for x in result.values()))
                self.assertEqual(len(attempts),6)
            finally:m.ROOT=prior
    def test_rejects_stale_content(self):
        with tempfile.TemporaryDirectory() as d:
            prior=m.ROOT
            try:
                m.ROOT=Path(d)
                for p in m.PATHS:(m.ROOT/p).write_text(p)
                with self.assertRaisesRegex(RuntimeError,"do not match"):
                    m.check(attempts=1,interval=0,fetch=lambda p,n:b"wrong")
            finally:m.ROOT=prior
    def test_requires_exact_production_origin(self):
        with self.assertRaises(ValueError):
            m.check(base="https://example.invalid/",attempts=1,interval=0,fetch=lambda p,n:b"fake")
if __name__=="__main__":unittest.main()
