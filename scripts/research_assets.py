"""Stockwatch research assets: offline inventory and private, rights-gated warehouse.

Public output is aggregate availability only. Never persist evaluation quotes.
The explicit rights manifest is a reviewed operator input, not proof of rights.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sqlite3, statistics
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from dataset_store import eligible

ROOT=Path(__file__).resolve().parents[1]
def read(root,name,default=None):
    p=root/name
    if not p.exists(): return {} if default is None else default
    return json.loads(p.read_text(encoding="utf-8"))
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False)
def digest(x): return hashlib.sha256(canon(x).encode()).hexdigest()
def https(x):
    if not isinstance(x,str): return False
    u=urlsplit(x)
    return u.scheme=="https" and bool(u.hostname) and not u.username and not u.password
def day(x):
    try: return isinstance(x,str) and date.fromisoformat(x).isoformat()==x
    except ValueError: return False
def finite(x): return type(x) in (float,int) and math.isfinite(x)
def now(): return datetime.now(timezone.utc).isoformat(timespec="seconds")

def report(root=ROOT):
    w=read(root,"watchlist.json").get("tickers",[])
    ids=read(root,"data/issuer-identities.json").get("entities",[])
    figi=read(root,"data/registered-source-status.json").get("figiCandidates",[])
    facts=read(root,"data/fundamentals.json").get("companies",{})
    history=read(root,"data/history-coverage.json")
    context=read(root,"data/context.json")
    # Actual file contents, not guessed counts. Only explicitly allowlisted datasets.
    open_sets=[d for d in read(root,"data/free-research.json").get("datasets",[]) if eligible(d)]
    known={r.get("ticker") for r in w}
    source_linked={r.get("ticker") for r in ids if r.get("ticker") in known and r.get("isin") and https(r.get("evidence"))}
    current_figi={r.get("ticker") for r in figi if r.get("ticker") in known}
    summary={"schemaVersion":1,"generated":now(),"sourceAsOf":history.get("generated"),
      "metrics":{"monitoredListings":len(known),"sourceLinkedIsins":len(source_linked),
        "figiCandidates":len(current_figi),"filingCompanies":len(facts),
        "filingFacts":sum(len(x.get("metrics",{})) for x in facts.values()),
        "openArchiveEligibleDatasets":len(open_sets),
        "licensedEquitySeries":history.get("licensedEquityHistory",{}).get("series",0),
        "licensedEquityObservations":history.get("licensedEquityHistory",{}).get("observations",0),
        "abIndicatorObservations":history.get("dailyABIndicators",{}).get("observations",0),
        "abIndicatorSeries":history.get("dailyABIndicators",{}).get("series",0),
        "currentComparablePairs":sum(p.get("latestPairEligible") is True for p in context.get("shareClasses",[])),
        "newsMetadataRecords":history.get("newsMetadata",{}).get("records",0)},
      "products":[
        {"id":"identity","title":"Instrument identity and corporate actions","status":"reference research","rights":"Review source rights before resale; FIGIs are candidates unless verified."},
        {"id":"fundamentals","title":"Source-linked financial facts","status":"initial filing coverage","rights":"Source-specific review; no resale authorization claimed."},
        {"id":"official","title":"Official economic data history","status":"archive-eligible source subset","rights":"Existing dataset allowlist and original attribution; evaluate commercial terms per dataset."},
        {"id":"quant","title":"Equity indicators and paired-market research","status":"licensed inputs required","rights":"No commercial redistribution of price-derived indicators without express permission."},
        {"id":"prices","title":"Historical equity price database","status":"licensed imports only","rights":"Permanent storage, public display and resale require separate authorization."}],
      "notice":"Availability inventory only. No entitlement, valuation, fresh quote or paid export is implied."}
    return summary

def rights(manifest, series, asof):
    # Only a local, reviewed agreement referencing this exact source and identity.
    if not isinstance(manifest,dict) or manifest.get("reviewed") is not True: return False
    required=("provider","sourceUrl","licenseReference","ticker","isin","mic","currency","adjusted")
    if any(series.get(k)!=manifest.get(k) for k in required): return False
    if not all(isinstance(manifest.get(k),str) and manifest[k].strip() for k in required if k!="adjusted"): return False
    if not https(manifest["sourceUrl"]) or not https(manifest["licenseReference"]): return False
    if type(manifest.get("adjusted")) is not bool or not day(asof): return False
    if manifest.get("evaluationOnly") is not False: return False
    if manifest.get("permanentInternalStorage") is not True or manifest.get("derivedResearch") is not True: return False
    if not day(manifest.get("validFrom")) or not day(manifest.get("validThrough")): return False
    return manifest["validFrom"]<=asof<=manifest["validThrough"]

def bars(series):
    b={}
    for r in series.get("bars",[]):
        d,c,v=r.get("date"),r.get("close"),r.get("volume")
        if not day(d) or d>date.today().isoformat() or not finite(c) or c<=0 or d in b: raise ValueError("invalid bar")
        if v is not None and (type(v) is not int or v<0): raise ValueError("invalid volume")
        b[d]=(float(c),v)
    return b

def equity_indicators(b):
    # Observed sessions only, no invented fills or annualization claims on thin samples.
    prices=[(d,c) for d,(c,v) in sorted(b.items()) if v is not None and v>0]
    if len(prices)<21: return []
    d=prices[-1][0]; closes=[c for _,c in prices[-21:]]
    returns=[math.log(y/x) for x,y in zip(closes,closes[1:])]
    peak=closes[0]; draw=0
    for c in closes:
        peak=max(peak,c);draw=min(draw,c/peak-1)
    return [(d,"return_20_observed_sessions",closes[-1]/closes[0]-1),
      (d,"daily_log_return_volatility_20",statistics.stdev(returns)),
      (d,"max_drawdown_21_observations",draw)]

def pair_indicators(a,b,relationship,fx=None):
    # Cross-listed securities require same ISIN and separate venues.
    # A/B requires explicitly verified distinct securities of same issuer.
    if relationship.get("verified") is not True or not https(relationship.get("sourceUrl")): return []
    if not a.get("isin") or not b.get("isin") or a.get("ticker")==b.get("ticker"): return []
    if (relationship.get("a"),relationship.get("b"))!=(a.get("ticker"),b.get("ticker")): return []
    if type(a.get("adjusted")) is not bool or a.get("adjusted")!=b.get("adjusted"): return []
    kind=relationship.get("kind")
    if kind=="cross_listing":
        if a["isin"]!=b["isin"] or not a.get("mic") or not b.get("mic") or a["mic"]==b["mic"]: return []
    elif kind=="share_class":
        if a["isin"]==b["isin"] or not relationship.get("issuerId"): return []
    else: return []
    aa,bb=bars(a),bars(b); aligned=[]
    for d in sorted(aa.keys()&bb.keys()):
        ac,av=aa[d];bc,bv=bb[d]
        if not av or not bv: continue
        # FX quote must be explicitly B currency per A currency, same date.
        if a.get("currency")!=b.get("currency"):
            if not fx or fx.get("base")!=a.get("currency") or fx.get("quote")!=b.get("currency") or fx.get("reviewed") is not True: return []
            factor=fx.get("rates",{}).get(d)
            if not finite(factor) or factor<=0: continue
            ac*=factor
        aligned.append((d,ac/bc))
    if len(aligned)<20: return []
    d,r=aligned[-1]; window=[v for _,v in aligned[-20:]]; sd=statistics.stdev(window)
    out=[(d,"aligned_close_ratio",r),(d,"ratio_observed_premium",r-1)]
    if sd>0: out.append((d,"ratio_zscore_20_aligned", (r-statistics.mean(window))/sd))
    return out

def private_build(root,db_path,approved_inputs=None,rights_by_ticker=None,asof=None):
    asof=asof or date.today().isoformat()
    db_path=Path(db_path).resolve()
    if db_path==root.resolve() or root.resolve() in db_path.parents: raise ValueError("private database must be outside repository")
    db_path.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(db_path)
    db.executescript((root/"database/0002_research_assets.sql").read_text(encoding="utf-8"))
    ids=read(root,"data/issuer-identities.json")
    with db:
        for r in ids.get("entities",[]):
            if not r.get("ticker") or not r.get("name") or not ids.get("generated"): continue
            ref={k:r.get(k) for k in ("ticker","name","mic","isin","evidence","previousTicker","previousIsin","effectiveDate","historyPolicy","corporateActionSource")}
            fp=digest(ref); source=r.get("evidence") if https(r.get("evidence")) else None
            db.execute("INSERT OR IGNORE INTO listing_observation VALUES (?,?,?,?,?,?,?,?)",(r["ticker"],ids["generated"],fp,r["name"],r.get("mic"),r.get("isin"),source,"source_linked" if source and r.get("isin") else "editorial"))
            action=r.get("corporateActionSource") or source
            if r.get("previousTicker") and r.get("historyPolicy") and https(action):
                db.execute("INSERT OR IGNORE INTO corporate_action_evidence VALUES (?,?,?,?,?,?,?,?)",(r["ticker"],fp,r.get("previousTicker"),r.get("previousIsin"),r.get("isin"),r.get("effectiveDate"),r["historyPolicy"],action))
        for ticker,r in read(root,"data/fundamentals.json").get("companies",{}).items():
            if not day(r.get("asOf")) or not https(r.get("sourceUrl")) or not r.get("currency") or not r.get("period"): continue
            for metric,value in r.get("metrics",{}).items():
                if finite(value):
                    db.execute("INSERT OR IGNORE INTO filing_fact VALUES (?,?,?,?,?,?,?,?,?)",(ticker,r["asOf"],r["period"],r.get("published") or "unknown",r["currency"],metric,value,r["sourceUrl"],digest(r)))
            m=r.get("metrics",{}); revenue=m.get("revenue")
            if finite(revenue) and revenue>0 and finite(m.get("operatingIncome")):
                db.execute("INSERT OR IGNORE INTO research_indicator VALUES (?,?,?,?,?,?,0)",(ticker,r["asOf"],"reported_operating_margin",m["operatingIncome"]/revenue,"filing_same_period_v1",digest(r)))
        for x in read(root,"data/free-research.json").get("datasets",[]):
            if not eligible(x): continue
            payload={k:v for k,v in x.items() if k not in ("retrievedAt","checkedAt","status")}
            db.execute("INSERT OR IGNORE INTO open_snapshot VALUES (?,?,?,?,?,?)",(x["id"],digest(payload),x["sourceUrl"],x["license"],x["retrievedAt"],canon(payload)))
        approved={}
        for s in approved_inputs or []:
            t=s.get("ticker"); m=(rights_by_ticker or {}).get(t)
            if not rights(m,s,asof): continue
            b=bars(s); h=digest(m)
            # Never overwrite a conflicting observation under the same entitlement.
            for d,(c,v) in b.items():
                key=(t,d,s["provider"],h)
                old=db.execute("SELECT close,volume FROM licensed_bar WHERE ticker=? AND session=? AND provider=? AND entitlement_hash=?",key).fetchone()
                if old is not None and old!=(c,v): raise ValueError("conflicting licensed observation; review correction")
                db.execute("INSERT OR IGNORE INTO licensed_bar VALUES (?,?,?,?,?,?,?,?,?,?)",(t,d,s["provider"],s["isin"],s["mic"],s["currency"],int(s["adjusted"]),c,v,h))
            approved[t]=(s,m)
            for d,k,v in equity_indicators(b):
                db.execute("INSERT OR IGNORE INTO research_indicator VALUES (?,?,?,?,?,?,?)",(t,d,k,v,"observed_sessions_v1",digest([h,s]),int(m.get("commercialDerivedRedistribution") is True)))
        # A/B / cross-listing results are available through the validated function;
        # no production relationship or FX licence is assumed. Never auto-join names.
    counts={t:db.execute("SELECT COUNT(*) FROM "+t).fetchone()[0] for t in ("listing_observation","corporate_action_evidence","filing_fact","open_snapshot","licensed_bar","research_indicator")}
    db.close()
    return counts

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--private-db");p.add_argument("--licensed-inputs");p.add_argument("--rights")
    a=p.parse_args()
    if bool(a.licensed_inputs)!=bool(a.rights) or (a.licensed_inputs and not a.private_db):p.error("licensed inputs and rights require private database")
    if a.private_db:
        inputs=json.loads(Path(a.licensed_inputs).read_text()) if a.licensed_inputs else []
        manifests=json.loads(Path(a.rights).read_text()) if a.rights else {}
        print("PRIVATE_RESEARCH_COUNTS "+json.dumps(private_build(ROOT,a.private_db,inputs,manifests)))
    else:
        dest=ROOT/"data/research-assets.json";tmp=dest.with_suffix(".tmp")
        tmp.write_text(json.dumps(report(),ensure_ascii=False,indent=2)+"\n",encoding="utf-8");tmp.replace(dest)
        print("RESEARCH_ASSETS "+json.dumps(report()["metrics"]))
if __name__=="__main__":main()
