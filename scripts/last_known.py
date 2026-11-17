"""Keep exact-identity dated observations during temporary source failures."""
import json,math
from datetime import date
def load(path):
    try:
        v=json.loads(path.read_text(encoding="utf8"))
        return v if isinstance(v,dict) else {}
    except (OSError,ValueError):
        return {}
def numeric(n):
    return type(n) in (float,int) and math.isfinite(n)
def dated(d):
    try:return isinstance(d,str) and date.fromisoformat(d).isoformat()==d
    except (TypeError,ValueError):return False
def valid(r,today):
    return isinstance(r,dict) and numeric(r.get("close")) and r["close"]>0 and dated(r.get("date")) and r["date"]<=today and bool(r.get("currency"))
def company_row(entry,fresh,old,today,stamp,prior_stamp):
    if not valid(old,today) or old.get("ticker")!=entry["ticker"] or old.get("name")!=entry.get("name",entry["ticker"]) or any(entry.get(k) and entry[k]!=old.get(k) for k in ("isin","mic","currency")):old=None
    if not valid(fresh,today) or (old and (fresh["date"]<old["date"] or fresh["currency"]!=old["currency"])):
        if old:
            fields=("date","close","currency","exchange","spark","changePct","sigma","volume","medianVolume","rvol","isin","mic")
            return {**entry,**{k:old[k] for k in fields if k in old},"stories":[],"priceStatus":"retained","priceObservedAt":old.get("priceObservedAt") or prior_stamp,"marketPct":None,"excessPct":None,"excessSigma":None}
        return {**entry,"stories":[],"unavailable":True,"priceStatus":"unavailable","marketPct":None,"excessPct":None,"excessSigma":None}
    return {**fresh,"priceStatus":"reported","priceObservedAt":stamp}
def context_rows(new,old,key,stamp,prior_stamp,today):
    fields=("ticker","unit") if key in ("commodities","freight") else ("a","b","currency")
    idfields=fields[:1] if key in ("commodities","freight") else fields[:2]
    dkey="date" if key in ("commodities","freight") else "priceDate"
    price="last" if key in ("commodities","freight") else "ratio"
    def ident(r):return tuple(r.get(k) for k in idfields)
    def valid(r):return numeric(r.get(price)) and dated(r.get(dkey)) and r[dkey]<=today and all(r.get(k) for k in fields)
    def retained(p):return {**p,"observationStatus":"retained","observedAt":p.get("observedAt") or prior_stamp,**({"latestPairEligible":False} if key=="shareClasses" else {})}
    prior={ident(r):r for r in old if valid(r)}
    out=[]
    for r in new:
        p=prior.pop(ident(r),None)
        if not valid(r):
            if p:out.append(retained(p))
            continue
        if p and all(p[k]==r[k] for k in fields) and p[dkey]>r[dkey]:out.append(retained(p))
        else:out.append({**r,"observationStatus":"reported","observedAt":stamp})
    out.extend(retained(p) for p in prior.values())
    return out
