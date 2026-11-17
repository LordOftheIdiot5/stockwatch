"""V54: append source-linked financial/identity revisions to the V46 private warehouse.

No network requests, inferred split adjustments, unlicensed equity bars or public data export.
Only existing repository reference/filing/event inputs and optional operator-reviewed filing batches.
"""
from __future__ import annotations
import argparse,json,sqlite3
from pathlib import Path
from research_assets import ROOT, read, digest, canon, finite, https, day, now

METRICS={"revenue","operatingIncome","adjustedOperatingIncome","netIncome","eps","dividendPerShare","marketCap","pe","pb","dividendYield","freeCashFlow","totalAssets","totalLiabilities","cash","totalDebt","equity","operatingCashFlow","capitalExpenditure","grossProfit"}

def filing(subject,x):
    if not isinstance(subject,str) or not subject or not isinstance(x,dict) or not day(x.get("asOf")) or not https(x.get("sourceUrl")):return None
    if not isinstance(x.get("period"),str) or not x["period"].strip() or not isinstance(x.get("currency"),str) or len(x["currency"])!=3 or not x["currency"].isupper():return None
    published=x.get("published")
    if published is not None and (not day(published) or published<x["asOf"]):return None
    metrics={k:v for k,v in (x.get("metrics") or {}).items() if k in METRICS and finite(v)}
    if not metrics:return None
    return dict(subject=subject,asOf=x["asOf"],period=x["period"],currency=x["currency"],published=published,sourceUrl=x["sourceUrl"],sourceName=x.get("sourceName"),metrics=metrics)

def identity(x):
    if not isinstance(x,dict) or not x.get("ticker") or not x.get("name"):return None
    out={k:x[k] for k in ("ticker","name","isin","mic","exchange","marketSegment","previousTicker","previousIsin","effectiveDate","historyPolicy","evidence","corporateActionSource") if x.get(k) is not None}
    if not https(out.get("evidence")):out.pop("evidence",None)
    if not https(out.get("corporateActionSource")):out.pop("corporateActionSource",None)
    if not day(out.get("effectiveDate")):out.pop("effectiveDate",None)
    return out

def event(x):
    if not isinstance(x,dict) or not x.get("ticker") or not day(x.get("date")) or not https(x.get("sourceUrl")) or not x.get("type"):return None
    # Retain explicit source status; provisional calendar records are not completed actions.
    return {k:x[k] for k in ("ticker","date","type","label","title","status","sourceUrl","confidence") if k in x}

def build(root, db_path, reviewed=None, observed_at=None):
    root=Path(root).resolve();db_path=Path(db_path).resolve()
    if db_path==root or root in db_path.parents:raise ValueError("warehouse must remain outside repository")
    db_path.parent.mkdir(parents=True,exist_ok=True)
    stamp=observed_at or now()
    with sqlite3.connect(db_path) as db:
        for p in ("0002_research_assets.sql","0003_financial_history.sql"):
            db.executescript((root/"database"/p).read_text(encoding="utf8"))
        raw=list(read(root,"data/fundamentals.json").get("companies",{}).items())
        for item in reviewed or []:
            if item.get("reviewed") is not True or item.get("internalRetentionPermitted") is not True or not https(item.get("rightsReference")):raise ValueError("new filing batch requires reviewed retention permission")
            raw.append((item.get("subject"),item.get("filing")))
        for subject,x in raw:
            f=filing(subject,x)
            if not f:continue
            fp=digest(f);k=(subject,f["asOf"],f["period"],f["currency"])
            prev=db.execute("SELECT fingerprint FROM financial_revision WHERE subject=? AND period_end=? AND period_label=? AND currency=? ORDER BY observed_at DESC,rowid DESC LIMIT 1",k).fetchone()
            db.execute("INSERT OR IGNORE INTO financial_revision VALUES (?,?,?,?,?,?,?,?,?,?)",(*k,fp,stamp,f["published"],f["sourceUrl"],canon(f),prev[0] if prev and prev[0]!=fp else None))
            for metric,value in f["metrics"].items():
                db.execute("INSERT OR IGNORE INTO filing_fact VALUES (?,?,?,?,?,?,?,?,?)",(subject,f["asOf"],f["period"],f["published"] or "unknown",f["currency"],metric,value,f["sourceUrl"],fp))
        for x in read(root,"data/issuer-identities.json").get("entities",[]):
            y=identity(x)
            if not y:continue
            t=y["ticker"];fp=digest(y);source=y.get("evidence") or y.get("corporateActionSource")
            prev=db.execute("SELECT fingerprint FROM identity_revision WHERE ticker=? ORDER BY observed_at DESC,rowid DESC LIMIT 1",(t,)).fetchone()
            db.execute("INSERT OR IGNORE INTO identity_revision VALUES (?,?,?,?,?,?)",(t,fp,stamp,source,canon(y),prev[0] if prev and prev[0]!=fp else None))
            action=y.get("corporateActionSource") or y.get("evidence")
            if (y.get("previousTicker") or y.get("previousIsin")) and y.get("historyPolicy") and https(action):
                db.execute("INSERT OR IGNORE INTO corporate_action_evidence VALUES (?,?,?,?,?,?,?,?)",(t,fp,y.get("previousTicker"),y.get("previousIsin"),y.get("isin"),y.get("effectiveDate"),y["historyPolicy"],action))
        for x in read(root,"data/events.json").get("items",[]):
            y=event(x)
            if y:db.execute("INSERT OR IGNORE INTO corporate_event_revision VALUES (?,?,?,?,?,?,?)",(y["ticker"],y["type"],y["date"],digest(y),stamp,y["sourceUrl"],canon(y)))
        return {t:db.execute("SELECT COUNT(*) FROM "+t).fetchone()[0] for t in ("financial_revision","filing_fact","identity_revision","corporate_action_evidence","corporate_event_revision")}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--private-db",required=True);p.add_argument("--reviewed-filings")
    a=p.parse_args();batch=json.loads(Path(a.reviewed_filings).read_text(encoding="utf8")) if a.reviewed_filings else []
    print("PRIVATE_FINANCIAL_HISTORY "+json.dumps(build(ROOT,a.private_db,batch),sort_keys=True))
if __name__=="__main__":main()
