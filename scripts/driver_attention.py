"""Observed archive activity, not market-wide news volume, hype or predicted upside."""
from collections import Counter
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from news_quality import norm
import re

TOPICS=("numbers","prices","operations","potential","risk")
VERSION=1

def stamp(v):
    try:
        d=datetime.fromisoformat(str(v).replace("Z","+00:00"))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (TypeError,ValueError,OverflowError):
        return None

def secure(url):
    try:
        u=urlsplit(url)
        return u.scheme=="https" and bool(u.hostname) and not u.username and not u.password
    except (TypeError,ValueError):
        return False

def potential_kind(item):
    """A headline topic only: never a project execution status or earnings forecast."""
    title=norm(item.get("headline"))
    if re.search(r"\b(profit warning|resultatvarsel|nedjuster)\b",title):return "Guidance / warning"
    if re.search(r"\b(guidance|outlook|forecast|prognos)\b",title):return "Guidance / outlook"
    if item.get("category")=="M&A":return "Transactions"
    if item.get("category")=="Contracts":return "Contracts / agreements"
    if re.search(r"\b(product launch|new project|expansion plans?|investment plans?|order backlog|new orders)\b",title):return "Projects / demand"
    return "Other potential-related topic"

def build(items,watchlist,seed,now):
    now=now.astimezone(timezone.utc)
    end=now.replace(hour=0,minute=0,second=0,microsecond=0)
    start=end-timedelta(days=14)
    dates=[(start+timedelta(days=i)).date().isoformat() for i in range(14)]
    identities={}
    for w in watchlist:
        if w.get("ticker"):identities[w["ticker"]]=w["ticker"]
    us={}
    for w in seed:
        if w.get("identityStatus")=="sec_ticker_exchange_association" and w.get("id") and w.get("symbol") and re.fullmatch(r"\d{10}",str(w.get("cik",""))):
            us[(w["symbol"],w["cik"])]=w["id"]
            identities[w["id"]]=w["id"]
    rows={k:{"listingId":k,"daily":[{"date":d,"issuer":0,"media":0} for d in dates],
             "potential":[],"observedRecords":0,"latestRecord":None,"topicCounts":{t:0 for t in TOPICS}}
          for k in sorted(identities)}
    seen=set()
    for item in items:
        if not isinstance(item,dict) or item.get("duplicateOf") or item.get("relevance") not in ("strong","mentioned"):continue
        t=stamp(item.get("published"))
        if not t or t>now or not item.get("id") or not secure(item.get("url")):continue
        is_sec=item.get("sourceFeed")=="sec_edgar"
        if is_sec:
            key=us.get((item.get("ticker"),item.get("sourceIssuer"))) if item.get("match")=="issuer_code" and item.get("relevance")=="strong" else None
        else:
            key=item.get("ticker") if item.get("ticker") in identities and item.get("ticker") not in us.values() else None
        if key not in rows or (key,item["id"]) in seen:continue
        seen.add((key,item["id"]))
        row=rows[key];row["observedRecords"]+=1
        ts=t.isoformat(timespec="seconds").replace("+00:00","Z")
        if not row["latestRecord"] or ts>row["latestRecord"]:row["latestRecord"]=ts
        issuer=item.get("relevance")=="strong" and item.get("match")=="issuer_code" and item.get("type")=="disclosure"
        if not issuer and item.get("relevance")!="mentioned":continue
        tags={x.get("driver") for x in item.get("driverTags",[]) if isinstance(x,dict) and x.get("driver") in TOPICS and isinstance(x.get("basis"),str)} if item.get("driverVersion")==1 else set()
        if start<=t<end:
            idx=(t.date()-start.date()).days
            row["daily"][idx]["issuer" if issuer else "media"]+=1
            if idx>=7:
                for tag in tags:row["topicCounts"][tag]+=1
        if now-timedelta(days=90)<=t<=now and "potential" in tags:
            row["potential"].append({"id":item["id"],"published":ts,"headline":item.get("headline",""),"url":item["url"],
                                     "evidence":"issuer" if issuer else "named_reference","topic":potential_kind(item)})
    for row in rows.values():
        row["prior7"]={k:sum(d[k] for d in row["daily"][:7]) for k in ("issuer","media")}
        row["recent7"]={k:sum(d[k] for d in row["daily"][7:]) for k in ("issuer","media")}
        row["potential"]=sorted(row["potential"],key=lambda x:(x["published"],x["id"]),reverse=True)[:20]
    return {"schemaVersion":VERSION,"generated":now.isoformat(timespec="seconds").replace("+00:00","Z"),
            "windowStart":dates[0],"windowEnd":dates[-1],
            "notice":"Counts are from this retained rolling archive, not comprehensive monitoring. Zero means no matching retained records, not no news. No attention, sentiment, hype, upside or price-impact score.",
            "listings":rows}
