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
from datetime import datetime, timezone, timedelta
from pathlib import Path
from last_known import valid, valid_move

ROOT = Path(__file__).resolve().parents[1]
OFFICIAL = frozenset({
    "data/open-data.json",
    "data/free-research.json",
    "data/research-index.json",
    "data/registered-source-status.json",
    "data/entsoe-open.json",
    "data/economic-feeds.json",
    "data/shipping-open.json",
    "data/shipping-ports.json",
    "data/shipping-connectivity.json",
    "data/instrument-directory.json",
    "data/research-coverage.json",
    "data/history-coverage.json",
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


def guarded_signals(incoming, previous, watchlist):
    """Reject malformed or destructive replacements of the existing published snapshot.

    Never restore a removed listing, substitute across identities, invent a date,
    or publish a saved row as a fresh signal. A failed check leaves main unchanged.
    """
    data=json.loads(incoming)
    old=json.loads(previous) if previous else {"companies":[]}
    expected=json.loads(watchlist)["tickers"]
    if not isinstance(data,dict) or not isinstance(data.get("companies"),list):
        raise ValueError("invalid scanner snapshot")
    def stamp(s):
        t=datetime.fromisoformat(s.replace("Z","+00:00"))
        if t.tzinfo is None:raise ValueError("missing scanner time zone")
        return t
    generated=stamp(data["generated"])
    if old.get("generated") and generated<stamp(old["generated"]):
        raise ValueError("scanner snapshot older than published data")
    rows=data["companies"]
    ids=[r["ticker"] for r in rows]
    expected_ids=[r["ticker"] for r in expected]
    if not expected_ids or len(ids)!=len(set(ids)) or set(ids)!=set(expected_ids):
        raise ValueError("incomplete or duplicate scanner listing coverage")
    today=generated.date().isoformat()
    prior={r["ticker"]:r for r in old.get("companies",[]) if isinstance(r,dict) and r.get("ticker")}
    for row in rows:
        p=prior.get(row["ticker"])
        if not p or not valid(p,today):continue
        # Only compare the identical listing. A security migration is handled
        # by the watchlist and identity policy, not by copying old quotes.
        if p.get("name")!=row.get("name") or any(row.get(k) and p.get(k)!=row[k] for k in ("isin","mic","currency")):continue
        if not valid(row,today) or row["date"]<p["date"]:
            raise ValueError("refusing loss or regression of saved observation: "+row["ticker"])
        if row["date"]==p["date"] and valid_move(p) and not valid_move(row):
            raise ValueError("refusing incomplete same-session replacement: "+row["ticker"])
    return incoming


def merge_unlisted_news(incoming, previous, registry):
    """Replay bounded eligible news against latest main, not the job's stale checkout."""
    from unlisted_news_n41 import candidate, DAYS, LIMIT
    from news_quality import norm
    from email.utils import format_datetime
    new=json.loads(incoming)
    old=json.loads(previous) if previous else {"schema":1,"attemptedAt":None,"items":[],"coverage":{}}
    companies={c["id"]:c for c in json.loads(registry)["companies"]}
    if new.get("schema")!=1 or old.get("schema")!=1:
        raise ValueError("invalid unlisted news schema")
    def stamp(value):
        t=datetime.fromisoformat(value.replace("Z","+00:00"))
        if t.tzinfo is None:raise ValueError("missing news time zone")
        return t.astimezone(timezone.utc)
    now=stamp(new["attemptedAt"])
    older=old.get("attemptedAt") and stamp(old["attemptedAt"])>now
    if older:
        now=stamp(old["attemptedAt"])
    latest=old if older else new
    items=[]
    coverage={}
    for ident,company in companies.items():
        eligible=[]
        for doc in (latest,new if older else old):
            for item in doc.get("items",[]):
                if item.get("company")!=ident or item.get("tier")!="named reference":
                    continue
                try:
                    date=stamp(item["date"])
                    if not now-timedelta(days=DAYS)<=date<=now:continue
                    raw={"title":item["title"],"url":item["url"],"publisher":item["publisher"],
                         "published":format_datetime(date)}
                    verified=candidate(company,raw,now)
                    if verified:eligible.append(verified)
                except (KeyError,ValueError,TypeError,OverflowError):
                    continue
        seen_titles=set()
        seen_ids=set()
        for row in sorted(eligible,key=lambda x:x["date"],reverse=True):
            k=norm(row["title"])
            if not k or k in seen_titles or row["id"] in seen_ids:continue
            seen_titles.add(k);seen_ids.add(row["id"]);items.append(row)
            if len(seen_ids)>=LIMIT:break
        c=dict(latest.get("coverage",{}).get(ident,{"status":"unconfirmed","freshNamedReferences":0}))
        c["retainedReferences"]=len(seen_ids)
        coverage[ident]=c
    result={**latest,"items":items,"coverage":coverage}
    return (json.dumps(result,ensure_ascii=False,indent=2)+"\n").encode("utf-8")


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
            if path=="data/signals.json":
                if content is None:raise ValueError("refusing deletion of published scanner snapshot")
                guarded_signals(content,dest.read_bytes() if dest.is_file() else None,(ROOT/"watchlist.json").read_bytes())
            if path=="data/unlisted-news-latest-n41.json":
                if content is None:raise ValueError("refusing deletion of unlisted news")
                content=merge_unlisted_news(content,dest.read_bytes() if dest.is_file() else None,
                    (ROOT/"data/unlisted-news-reviewed-n41.json").read_bytes())
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
