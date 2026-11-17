"""Conservative completed-session freshness checks; not an exchange calendar."""
from datetime import datetime, timezone, timedelta, date
import math

def comparison_date(now):
    now=now.astimezone(timezone.utc)
    day=now.date()-timedelta(days=now.hour<22)
    while day.weekday()>=5:
        day-=timedelta(days=1)
    return day.isoformat()

def number(v):
    return type(v) in (float,int) and math.isfinite(v)

def price_quality(row, target):
    if not row or row.get("unavailable") or not number(row.get("close")) or row["close"]<=0 or not number(row.get("changePct")):
        return "unavailable"
    day=row.get("date")
    try:
        if date.fromisoformat(day).isoformat()!=day or day>target:return "unconfirmed"
    except (TypeError,ValueError):
        return "unconfirmed"
    volume=row.get("volume")
    if not number(volume) or volume<0:return "unconfirmed"
    if volume==0:return "no_volume"
    return "older" if day<target else "comparable"

def coverage(snapshot,watchlist,context,now):
    target=comparison_date(now)
    rows={x["ticker"]:x for x in snapshot.get("companies",[]) if x.get("ticker")}
    counts={k:0 for k in ("comparable","older","no_volume","unconfirmed","unavailable")}
    for entry in watchlist.get("tickers",[]):
        counts[price_quality(rows.get(entry.get("ticker")),target)]+=1
    pairs=context.get("shareClasses") or []
    eligible=sum(p.get("priceDate")==target and p.get("aLatestDate")==target and p.get("bLatestDate")==target and p.get("latestPairEligible") is True and bool(p.get("currency")) for p in pairs)
    total=sum(counts.values())
    return {"comparisonDate":target,"equities":counts,"total":total,"comparablePairs":eligible,"reportedPairs":len(pairs),
            "status":"unknown" if not total else "degraded" if counts["comparable"]<total*.9 or eligible<len(pairs) else "coverage_ok",
            "method":"Conservative 22:00 UTC weekday cutoff; no exchange-specific holidays; not a live-quote guarantee."}

def current_alerts(snapshot,now):
    target=comparison_date(now)
    rows={x["ticker"]:x for x in snapshot.get("companies",[]) if x.get("ticker")}
    comparable=sum(price_quality(x,target)=="comparable" for x in rows.values())
    return [a for a in snapshot.get("alerts",[]) if a.get("fresh") and (a.get("kind")!="price" or
        (comparable>=10 and price_quality(rows.get(a.get("ticker")),target)=="comparable" and a.get("key")==f"px:{a.get('ticker')}:{target}"))]

def completed_market_baseline(rows,now,minimum=10):
    """Only compare observations from the same completed session."""
    target=comparison_date(now)
    sample=[x["changePct"] for x in rows if price_quality(x,target)=="comparable"]
    if len(sample)<minimum:return None,len(sample)
    from statistics import median
    return median(sample),len(sample)
