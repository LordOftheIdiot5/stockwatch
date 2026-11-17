"""Small same-provider diagnostic. Logs status, never price values."""
import json, urllib.request
from datetime import datetime,timezone
import context
from daily_recovery import missing_target,exact_day_url,extract,merge_exact_day

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
                status["accepted"]=merge_exact_day(data,other,ticker,now) is not None
            except Exception as e:
                status["status"]=type(e).__name__
        print("RECOVERY_DIAGNOSTIC "+json.dumps(status),flush=True)
if __name__=="__main__":main()
