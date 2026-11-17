"""Scanner adapter for already imported, provider-authorized daily closes.

No network calls, new subscriptions or permission assumptions.
A present but invalid licensed file fails closed. Do not combine sources.
"""
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
import json,math,re

CURRENCY={"OL":"NOK","ST":"SEK","CO":"DKK","HE":"EUR","MI":"EUR","VI":"EUR","DE":"EUR","BR":"EUR","PA":"EUR","MC":"EUR","HK":"HKD","AS":"EUR","IR":"EUR"}

def valid_url(u):
    if not isinstance(u,str):return False
    p=urlsplit(u)
    return p.scheme=="https" and bool(p.hostname) and not p.username and not p.password

def number(x):
    return type(x) in (int,float) and math.isfinite(x)

def licensed_chart(root, entry, now, required=22):
    ticker=entry["ticker"]
    if not re.fullmatch(r"[A-Za-z0-9.\-_=^]{1,40}",ticker):raise ValueError("invalid_ticker")
    path=Path(root)/"data"/"history"/(ticker+".json")
    if not path.exists():return None
    if not path.is_file() or path.stat().st_size>12_000_000:raise ValueError("history_file_limit")
    doc=json.loads(path.read_text(encoding="utf8"))
    expected=CURRENCY.get(ticker.rsplit(".",1)[-1])
    if (doc.get("ticker")!=ticker or not expected or doc.get("currency")!=expected
            or doc.get("redistributionPermitted") is not True or doc.get("adjusted") is not False
            or not isinstance(doc.get("source"),str) or not doc["source"].strip()
            or not valid_url(doc.get("sourceUrl")) or not valid_url(doc.get("licenseReference"))):
        raise ValueError("invalid_licensed_history_identity_or_entitlement")
    bars=[];seen=set()
    for b in doc.get("bars",[]):
        d=b.get("date")
        try:day=date.fromisoformat(d)
        except (TypeError,ValueError):raise ValueError("invalid_date") from None
        if day.isoformat()!=d or day>now.date() or d in seen:raise ValueError("invalid_or_duplicate_date")
        seen.add(d)
        close,vol=b.get("close"),b.get("volume")
        if not number(close) or close<=0 or not number(vol) or vol<0 or int(vol)!=vol:raise ValueError("invalid_close_or_volume")
        bars.append({"date":d,"close":close,"volume":vol})
    if len(bars)<required:raise ValueError("insufficient_licensed_history")
    bars.sort(key=lambda x:x["date"])
    return {"ticker":ticker,"exchange":entry.get("exchange"),"currency":expected,"bars":bars,
            "priceProvenance":{"provider":doc["source"],"sourceUrl":doc["sourceUrl"],
              "licenseReference":doc["licenseReference"],"redistributionPermitted":True,
              "adjusted":False,"input":"licensed_daily_history"}}

def select_chart(root,entry,now,legacy,required=22,licensed_only=False):
    try:licensed=licensed_chart(root,entry,now,required)
    except (OSError,ValueError,TypeError,KeyError,AttributeError) as e:
        # Never hide a bad licensed identity, missing volume or conflicting
        # rights by silently falling back to a different vendor.
        return None,"licensed_history_invalid"
    if licensed:return licensed,"licensed_history"
    if licensed_only:return None,"licensed_history_missing"
    data=legacy(entry["ticker"])
    if not data:return None,"legacy_unavailable"
    return {**data,"priceProvenance":{"provider":"Existing chart provider",
              "input":"legacy_chart","publicationRights":"not_verified"}},"legacy_chart"
