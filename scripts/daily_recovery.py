"""Bounded, opt-in recovery from the existing chart provider's exact-day daily response.
No quote metadata substitution, intraday aggregation, or access-limit bypass.
"""
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo
from urllib.parse import quote, urlencode
from copy import deepcopy
import json, math, os
from price_freshness import comparison_date

FIELDS=("open","high","low","close","volume")
MAX_RECOVERIES=12
_attempts=0

def positive(value):
    return type(value) in (int,float) and math.isfinite(value) and value>0

def extract(payload):
    result=(payload.get("chart") or {}).get("result") or []
    return result[0] if result else None

def missing_target(block,now):
    if not isinstance(block,dict):return None
    meta=block.get("meta") or {}
    if meta.get("instrumentType")!="EQUITY" or meta.get("dataGranularity")!="1d":return None
    stamps=block.get("timestamp") or []
    if not stamps or stamps[-1]!=max(stamps):return None
    try:
        zone=ZoneInfo(meta["exchangeTimezoneName"])
        day=datetime.fromtimestamp(stamps[-1],zone).date()
    except (KeyError,ValueError,TypeError,OverflowError):return None
    if day.isoformat()!=comparison_date(now):return None
    q=(block.get("indicators",{}).get("quote") or [{}])[0]
    i=len(stamps)-1
    def at(k):
        arr=q.get(k) or []
        return arr[i] if i<len(arr) else None
    if positive(at("close")):return None
    return (day,zone,stamps[-1])

def exact_day_url(ticker,day,zone):
    start=int(datetime.combine(day,time.min,zone).timestamp())
    end=int(datetime.combine(day+timedelta(days=1),time.min,zone).timestamp())
    params=urlencode({"period1":start,"period2":end,"interval":"1d","includePrePost":"false"})
    return "https://query1.finance.yahoo.com/v8/finance/chart/"+quote(ticker,safe="")+"?"+params

def merge_exact_day(original,replacement,ticker,now):
    target=missing_target(original,now)
    if not target or not isinstance(replacement,dict):return None
    day,zone,stamp=target
    a,b=original.get("meta") or {},replacement.get("meta") or {}
    if a.get("symbol")!=ticker or b.get("symbol")!=ticker:return None
    if any(not a.get(k) or a.get(k)!=b.get(k) for k in ("currency","exchangeName","exchangeTimezoneName","instrumentType","dataGranularity")):return None
    stamps=replacement.get("timestamp") or []
    if stamps!=[stamp]:return None
    q=(replacement.get("indicators",{}).get("quote") or [{}])[0]
    if any(not isinstance(q.get(k),list) or len(q[k])!=1 or not positive(q[k][0]) for k in FIELDS):return None
    o,h,l,c,v=(q[k][0] for k in FIELDS)
    if not l<=min(o,c)<=max(o,c)<=h:return None
    out=deepcopy(original)
    dest=(out.get("indicators",{}).get("quote") or [{}])[0]
    count=len(out["timestamp"])
    if any(not isinstance(dest.get(k),list) or len(dest[k])!=count for k in FIELDS):return None
    for k in FIELDS:dest[k][-1]=q[k][0]
    out["_stockwatchRecovery"]={"method":"same_provider_exact_day_daily_bar","date":day.isoformat()}
    return out

def maybe_recover(block,ticker,fetch,now=None):
    global _attempts
    if os.environ.get("STOCKWATCH_ENABLE_EXACT_DAY_RECOVERY")!="true" or _attempts>=MAX_RECOVERIES:return block
    now=now or datetime.now(timezone.utc)
    target=missing_target(block,now)
    if not target:return block
    _attempts+=1
    try:
        raw=fetch(exact_day_url(ticker,target[0],target[1]))
        replacement=extract(json.loads(raw))
        merged=merge_exact_day(block,replacement,ticker,now)
        return merged if merged is not None else block
    except Exception:
        return block
