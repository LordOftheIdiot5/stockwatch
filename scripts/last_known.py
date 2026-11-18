"""Keep exact-identity dated observations during temporary source failures."""
import json,math
from datetime import date,timedelta
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
def valid_move(r):
    return numeric(r.get('changePct')) and numeric(r.get('volume')) and r['volume']>0
def _company_row(entry,fresh,old,today,stamp,prior_stamp):
    if not valid(old,today) or old.get("ticker")!=entry["ticker"] or old.get("name")!=entry.get("name",entry["ticker"]) or any(entry.get(k) and entry[k]!=old.get(k) for k in ("isin","mic","currency")):old=None
    # A partial response for the same session must not erase an intact saved
    # observation. Preserve the entire prior row, not a hybrid price/return.
    partial_same_day=bool(old and valid(fresh,today) and fresh["date"]==old["date"] and valid_move(old) and not valid_move(fresh))
    if not valid(fresh,today) or partial_same_day or (old and (fresh["date"]<old["date"] or fresh["currency"]!=old["currency"])):
        if old:
            fields=("date","close","currency","exchange","spark","changePct","sigma","volume","medianVolume","rvol","isin","mic")
            return {**entry,**{k:old[k] for k in fields if k in old},"stories":[],"priceStatus":"retained","priceObservedAt":old.get("priceObservedAt") or prior_stamp,"marketPct":None,"excessPct":None,"excessSigma":None}
        return {**entry,"stories":[],"unavailable":True,"priceStatus":"unavailable","marketPct":None,"excessPct":None,"excessSigma":None}
    return {**fresh,"priceStatus":"reported","priceObservedAt":stamp}
def company_row(entry,fresh,old,today,stamp,prior_stamp,seed=None):
    """Keep the last positive-volume movement separate from a newer price."""
    row = _company_row(entry,fresh,old,today,stamp,prior_stamp)
    if not valid(row,today) or valid_move(row):
        row.pop("lastValidMovement",None)
        return row
    def candidate(x):
        if not valid(x,today) or not valid_move(x) or x["date"] >= row["date"]:
            return False
        return all(x.get(k)==row.get(k) for k in ("ticker","name","currency","exchange","isin","mic"))
    sources = [old, (old or {}).get("lastValidMovement"), fresh, seed]
    # An old nested observation may not cross a listing identity change.
    options = [x for x in sources if candidate(x)]
    if options:
        x = max(options,key=lambda x:x["date"])
        keys = ("ticker","name","currency","exchange","isin","mic","date","close","volume","changePct","sourceCommit","priceObservedAt")
        row["lastValidMovement"] = {k:x[k] for k in keys if k in x}
    else:
        row.pop("lastValidMovement",None)
    return row

def preserve_pair_moves(row, *sources):
    """A newer retained pair price must not discard a valid earlier return."""
    for side in ("a","b"):
        daily, saved = side+"DailyMove", side+"SavedDailyMove"
        def normalize(m):
            if not isinstance(m,dict) or m.get("method")!="individual_daily_closes" or not dated(m.get("date")) or not dated(m.get("previousDate")) or not numeric(m.get("changePct")) or m["changePct"] < -100 or not numeric(m.get("close")) or m["close"]<=0 or m.get("ticker")!=row.get(side) or m.get("currency")!=row.get("currency"):
                return None
            d=date.fromisoformat(m["date"])
            if d.weekday()>=5:return None
            prev=d-timedelta(days=1)
            while prev.weekday()>=5:prev-=timedelta(days=1)
            if m["previousDate"]!=str(prev) or m["date"]>row["priceDate"]:return None
            return m
        def direct(p):
            m=p.get(daily)
            if not isinstance(m,dict) or m.get("date")!=p.get("priceDate"):return None
            return normalize({**m,"ticker":p.get(side),"currency":p.get("currency"),"close":p.get(side+"Price")})
        options=[]
        for p in (row,*sources):
            if not p or any(p.get(k)!=row.get(k) for k in ("a","b","currency")):continue
            for m in (direct(p),normalize(p.get(saved))):
                if m and (m["date"]<row["priceDate"] or m["close"]==row.get(side+"Price")):options.append(m)
        row.pop(saved,None)
        if direct(row):continue
        if options:
            m=max(options,key=lambda m:m["date"])
            row[saved]={k:m[k] for k in ("date","previousDate","changePct","method","close","ticker","currency")}
    return row

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
        if p and all(p[k]==r[k] for k in fields) and p[dkey]>r[dkey]:chosen=retained(p)
        else:chosen={**r,"observationStatus":"reported","observedAt":stamp}
        out.append(preserve_pair_moves(chosen,p,r) if key=="shareClasses" else chosen)
    out.extend(retained(p) for p in prior.values())
    return out
