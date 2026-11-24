import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from build_public_pages_v122 import build,MANIFEST
from verify_pages_release import PATHS,EXCLUDED_PATHS

class PublicPagesTest(unittest.TestCase):
    def test_actual_manifest_and_release_parity(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"public"
            build(ROOT,out,json.loads(MANIFEST.read_text()))
            for p in PATHS:
                self.assertEqual((out/p).read_bytes(),(ROOT/p).read_bytes(),p)
            for p in ("docs","tests","database","deploy","worker",".github","scripts/nordl-private-storage-v122.mjs","data/seen.json"):
                self.assertFalse((out/p).exists(),p)
            for p in EXCLUDED_PATHS:
                self.assertFalse((out/p).exists(),p)
            self.assertEqual([p.name for p in (out/"scripts").iterdir()],["maritime-pulse-v121.mjs"])
    def test_every_pages_upload_uses_isolated_artifact(self):
        # Scan-generated data commits have a separate deploy job. Never let
        # another workflow bypass the publication manifest.
        uploads=[]
        for path in sorted((ROOT/".github/workflows").glob("*.y*ml")):
            workflow=path.read_text(encoding="utf-8")
            for chunk in workflow.split("uses: actions/upload-pages-artifact@")[1:]:
                with self.subTest(workflow=path.name):
                    step=chunk.split("\n      - ",1)[0]
                    self.assertIn("path: ${{ runner.temp }}/stockwatch-public",step)
                    self.assertIn('python scripts/build_public_pages_v122.py --out "$RUNNER_TEMP/stockwatch-public"',workflow)
                    self.assertIn("python tests/test_public_pages_v122.py",workflow)
                    self.assertIn("python scripts/verify_pages_release.py",workflow)
                uploads.append(path.name)
        self.assertEqual(sorted(uploads),["open-data.yml","pages.yml","scan.yml"])
    def test_unknown_paths_not_published_and_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);root=base/"repo";root.mkdir()
            (root/"index.html").write_text("public")
            (root/"private.json").write_text("private")
            m={"files":["index.html"],"patterns":[]}
            build(root,base/"public",m)
            self.assertFalse((base/"public/private.json").exists())
            (root/"link.html").symlink_to(root/"private.json")
            with self.assertRaises(ValueError):
                build(root,base/"bad",{"files":["link.html"],"patterns":[]})
            with self.assertRaises(ValueError):
                build(root,base/"bad2",{"files":["../outside"],"patterns":[]})
            with self.assertRaises(ValueError):
                build(root,root/"out",m)

if __name__=="__main__":
    unittest.main()
