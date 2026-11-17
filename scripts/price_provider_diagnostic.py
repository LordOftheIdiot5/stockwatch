"""Small same-provider diagnostic. Logs status, never price values."""
import json, urllib.request
from datetime import timedelta, time
from urllib.parse import urlencode, quote
from urllib.error import HTTPError
from datetime import datetime,timezone
import context
from daily_recovery import missing_target,exact_day_url,extract,merge_exact_day,recovery_validation

def main():
    now=datetime.now(timezone.utc)
    for ticker in ("WWI.OL","WWIB.OL","ERIC-A.ST","ERIC-B.ST"):
        data=context._chart(ticker,rng="1y")
        health=context.latest_bar_health(data)
        print("PRICE_DIAGNOSTIC "+json.dumps({"ticker":ticker,"window":"1y",**health}),flush=True)
        target=missing_target(data,now)
        status={"ticker":ticker,"method":"exact_day_regular_session_daily","accepted":False,"status":"not_eligible"}
        if target:
            try:
                req=urllib.request.Request(exact_day_url(ticker,target[0],target[1]),headers={"User-Agent":context.UA})
                with urllib.request.urlopen(req,timeout=context.TIMEOUT) as response:
                    other=extract(json.load(response))
                status.update(context.latest_bar_health(other))
                status["validation"]=recovery_validation(data,other,ticker,now)
                status["accepted"]=merge_exact_day(data,other,ticker,now) is not None
            except Exception as e:
                status["status"]=type(e).__name__
        print("RECOVERY_DIAGNOSTIC "+json.dumps(status),flush=True)
        if target:
            day,zone,_=target
            # See whether an explicit long window retrieves the whole series
            # including the completed day, without extra per-symbol retries.
            params=urlencode({"period1":int(datetime.combine(day-timedelta(days=365),time.min,zone).timestamp()),
                "period2":int(datetime.combine(day+timedelta(days=1),time.min,zone).timestamp()),
                "interval":"1d","includePrePost":"false"})
            out={"ticker":ticker,"method":"explicit_year_window","eligible":False}
            try:
                req=urllib.request.Request("https://query1.finance.yahoo.com/v8/finance/chart/"+quote(ticker,safe="")+"?"+params,headers={"User-Agent":context.UA})
                with urllib.request.urlopen(req,timeout=context.TIMEOUT) as response:
                    full=extract(json.load(response))
                h=context.latest_bar_health(full)
                meta=(full or {}).get("meta") or {}
                orig=data.get("meta") or {}
                valid,_=context.valid_pair_closes(full or {})
                out.update(h)
                out["validObservations"]=len(valid)
                out["eligible"]=h["status"]=="valid_bar" and h["lastValidDate"]==day.isoformat() and len(valid)>=60 and meta.get("symbol")==ticker and all(orig.get(k) and orig[k]==meta.get(k) for k in ("currency","exchangeName","exchangeTimezoneName","instrumentType","dataGranularity"))
            except HTTPError as e:
                out["status"]="http_error";out["httpStatus"]=e.code
                if e.code in (401,403,429):
                    print("WINDOW_DIAGNOSTIC "+json.dumps(out),flush=True)
                    return
            except Exception as e:
                out["status"]=type(e).__name__
            print("WINDOW_DIAGNOSTIC "+json.dumps(out),flush=True)
if __name__=="__main__":main()
