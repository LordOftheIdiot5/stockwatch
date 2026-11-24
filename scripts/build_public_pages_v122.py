"""Build public Pages artifact only from reviewed paths. No network or source collection."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name("public-pages-manifest-v122.json")

def build(root, out, manifest):
    root, out = Path(root).resolve(), Path(out).resolve()
    if out == root or root in out.parents or out in root.parents:
        raise ValueError("Output must be an isolated directory outside checkout")
    if out.exists():
        raise ValueError("Output must not already exist")
    paths = set(manifest["files"])
    patterns = [re.compile(p) for p in manifest["patterns"]]
    for folder in ("data/news-store", "data/sec-companyfacts"):
        d = root / folder
        if d.is_symlink():
            raise ValueError("Symlinked source directory")
        if d.is_dir():
            for p in d.iterdir():
                rel = p.relative_to(root).as_posix()
                if any(pattern.fullmatch(rel) for pattern in patterns):
                    paths.add(rel)
    # Fail closed on missing required paths, traversal, symlinks and private prefixes.
    for rel in sorted(paths):
        p = root / rel
        if Path(rel).is_absolute() or ".." in Path(rel).parts or any(part.startswith(".") for part in Path(rel).parts):
            raise ValueError("Unsafe manifest path")
        if rel.startswith(("tests/","docs/","database/","deploy/","worker/")) or (rel.startswith("scripts/") and rel != "scripts/maritime-pulse-v121.mjs"):
            raise ValueError("Private manifest path")
        if not p.is_file() or any(q.is_symlink() for q in [p,*p.parents] if q != root and root in q.parents):
            raise ValueError("Missing or unsafe required file: " + rel)
    out.mkdir(parents=True)
    for rel in sorted(paths):
        dest = out / rel
        dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(root / rel,dest)
    (out / ".nojekyll").touch()
    actual = {p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()}
    if actual != paths | {".nojekyll"}:
        raise ValueError("Unexpected artifact contents")
    return {"files":len(paths),"bytes":sum((out / p).stat().st_size for p in paths)}

if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    print(json.dumps(build(ROOT,a.out,json.loads(MANIFEST.read_text())),sort_keys=True))
