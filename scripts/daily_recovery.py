"""Bounded, opt-in recovery from the existing chart provider's exact-day daily response.
No quote metadata substitution, intraday aggregation, or access-limit bypass.
"""
from datetime import datetime, timezone, timedelta, time
from zoneinfo import ZoneInfo
from urllib.parse import quote, urlencode
from copy import deepcopy
import json, math, os
from urllib.error import HTTPError
from price_freshness import comparison_date

FIELDS=("open","high","low","close","volume")
MAX_RECOVERIES=12
_attempts=0
_stopped=False

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

def recovery_validation(original,replacement,ticker,now):
    target=missing_target(original,now)
    if not target:return "original_not_eligible"
    if not isinstance(replacement,dict):return "replacement_unavailable"
    day,zone,stamp=target
    a,b=original.get("meta") or {},replacement.get("meta") or {}
    if a.get("symbol")!=ticker or b.get("symbol")!=ticker:return "symbol_mismatch"
    for k in ("currency","exchangeName","exchangeTimezoneName","instrumentType","dataGranularity"):
        if not a.get(k) or not b.get(k):return "missing_metadata_"+k
        if a[k]!=b[k]:return "metadata_mismatch_"+k
    stamps=replacement.get("timestamp") or []
    if len(stamps)!=1:return "unexpected_bar_count"
    try:
        if datetime.fromtimestamp(stamps[0],zone).date()!=day:return "session_date_mismatch"
    except (ValueError,TypeError,OverflowError):return "invalid_timestamp"
    # A daily bar identifies an exchange-local session, not an intraday instant.
    # Keep the original daily series timestamp to preserve alignment.
    q=(replacement.get("indicators",{}).get("quote") or [{}])[0]
    for k in FIELDS:
        if not isinstance(q.get(k),list) or len(q[k])!=1 or not positive(q[k][0]):return "invalid_"+k
    o,h,l,c,v=(q[k][0] for k in FIELDS)
    if not l<=min(o,c)<=max(o,c)<=h:return "inconsistent_ohlc"
    dest=(original.get("indicators",{}).get("quote") or [{}])[0]
    count=len(original["timestamp"])
    if any(not isinstance(dest.get(k),list) or len(dest[k])!=count for k in FIELDS):return "original_column_shape"
    try:
        if sum(datetime.fromtimestamp(x,zone).date()==day for x in original["timestamp"])!=1:return "ambiguous_original_session"
    except (ValueError,TypeError,OverflowError):return "invalid_original_timestamp"
    return "accepted_exact_timestamp" if stamps[0]==stamp else "accepted_same_local_session"

def merge_exact_day(original,replacement,ticker,now):
    status=recovery_validation(original,replacement,ticker,now)
    if not status.startswith("accepted_"):return None
    day,zone,stamp=missing_target(original,now)
    out=deepcopy(original)
    dest=out["indicators"]["quote"][0]
    q=replacement["indicators"]["quote"][0]
    for k in FIELDS:dest[k][-1]=q[k][0]
    out["_stockwatchRecovery"]={"method":"same_provider_exact_day_daily_bar","date":day.isoformat(),"validation":status}
    return out

def maybe_recover(block,ticker,fetch,now=None):
    global _attempts,_stopped
    if _stopped:return block
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
    except HTTPError as error:
        if error.code in (401,403,429):_stopped=True
        return block
    except Exception:
        return block
