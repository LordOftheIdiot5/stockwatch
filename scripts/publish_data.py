"""Publish generated data after other workflows push, without force-pushing.

Runs only inside a GitHub Actions checkout. Replays THIS job's changed data
files onto the latest remote main, re-merging the shared dataset catalog.
No API keys, personal records or credentials are stored here.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = frozenset({
    "data/open-data.json",
    "data/registered-source-status.json",
    "data/economic-feeds.json",
    "data/shipping-open.json",
    "data/shipping-ports.json",
})
CATALOG = "data/dataset-catalog.json"


def git(*args, check=True):
    return subprocess.run(["git", *args], cwd=ROOT, check=check,
                          capture_output=True, text=False)


def read_catalog(raw):
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and isinstance(data.get("datasets"), list):
            return data
    except (TypeError, ValueError):
        pass
    return {"datasets": []}


def merge_catalog(remote, generated, mode):
    """Keep the other producer's catalog entries when writing our own."""
    remote = read_catalog(remote)
    generated = read_catalog(generated)
    managed = (lambda path: path in OFFICIAL) if mode == "official" else (lambda path: path not in OFFICIAL)
    incoming = [entry for entry in generated["datasets"] if
                isinstance(entry, dict) and managed(entry.get("path"))]
    index = {entry.get("path") for entry in incoming}
    # Replace only records this run explicitly updated; retain all unrelated
    # remote rows, including scanner rows omitted from a partial snapshot.
    items = [entry for entry in remote["datasets"] if
             isinstance(entry, dict) and entry.get("path") not in index]
    remote["datasets"] = items + incoming
    remote["generated"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return (json.dumps(remote, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def publish(mode, retries=5):
    git("config", "user.name", "stockwatch")
    git("config", "user.email", "actions@github.com")
    git("add", "-A", "--", "data/")
    staged = git("diff", "--cached", "--name-only", "-z", "--", "data/").stdout
    changed = [x.decode("utf-8") for x in staged.split(b"\0") if x]
    if not changed:
        print("No generated data changes to publish.")
        return
    if any(not p.startswith("data/") or ".." in Path(p).parts for p in changed):
        raise ValueError("invalid_changed_path")
    snapshots = {p: (ROOT / p).read_bytes() if (ROOT / p).is_file() else None
                 for p in changed}
    previous_catalog = snapshots.get(CATALOG)
    for attempt in range(retries):
        git("fetch", "--no-tags", "origin", "main")
        # This is an ephemeral Actions checkout; snapshots above preserve only
        # files produced by this job while remote main is updated safely.
        git("reset", "--hard", "FETCH_HEAD")
        for path, content in snapshots.items():
            if path == CATALOG:
                continue
            dest = ROOT / path
            if content is None:
                dest.unlink(missing_ok=True)
            else:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(content)
        if previous_catalog is not None:
            dest = ROOT / CATALOG
            current = dest.read_bytes() if dest.is_file() else b"{}"
            dest.write_bytes(merge_catalog(current, previous_catalog, mode))
        git("add", "-A", "--", "data/")
        if git("diff", "--cached", "--quiet", check=False).returncode == 0:
            print("Generated data already up to date; no commit needed.")
            return
        git("commit", "-m", f"{mode}: source refresh")
        result = git("push", "origin", "HEAD:main", check=False)
        if result.returncode == 0:
            print(f"Published generated data (attempt {attempt + 1}).")
            return
        if attempt == retries - 1:
            raise RuntimeError("Non-fast-forward publication retries exhausted; data not published")
        print(f"Another workflow updated main; reapplying generated data (attempt {attempt + 2}).")
        time.sleep(2)
    raise RuntimeError("unreachable")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("scan", "official"))
    args = parser.parse_args()
    publish(args.mode)
