"""Europe-first and USA-first metadata probes; never publish or persist restricted quotes.

Turquoise: audit a locally obtained authorized daily CSV/GZIP by ISIN only.
Finazon: explicit authorized trial smoke; only response validation counts.
"""
import argparse,csv,gzip,json,math,os,re,time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen,HTTPRedirectHandler,build_opener
from urllib.parse import urlencode
from exchange_identity import valid_isin

FINAZON="https://api.finazon.io/v2.0/finazon/us_stocks_essential/time_series"
TRIAL=("AAPL","TSLA","GOOG")
LSEG_FIELDS={"trading date and time","instrument identification code","price","price currency",
             "price notation","quantity","venue of execution","publication date and time",
             "venue of publication","transaction identification code","flags","trading system"}

def date_utc(s):
    d=datetime.fromisoformat(s.strip().replace("Z","+00:00"))
    if d.tzinfo is None:raise ValueError("timestamp_without_timezone")
    return d.astimezone(timezone.utc).date().isoformat()

def turquoise_audit(stream,expected_date,target_isins=()):
    reader=csv.DictReader(stream,delimiter=";")
    headers=[h.strip().lower() for h in reader.fieldnames or []]
    if len(headers)!=len(set(headers)) or set(headers)!=LSEG_FIELDS:
        raise ValueError("unexpected TGHE schema")
    reader.fieldnames=headers
    target=set(target_isins)
    if any(not valid_isin(x) for x in target):raise ValueError("invalid target ISIN")
    seen=set();counts=Counter()
    for row in reader:
        counts["reportRows"]+=1
        if counts["reportRows"]>10_000_000:raise ValueError("row_limit")
        if None in row or any(v is None for v in row.values()):raise ValueError("malformed row")
        isin=row["instrument identification code"].strip()
        if not valid_isin(isin):
            counts["invalidISIN"]+=1;continue
        if row["venue of execution"].strip()!="TGHE":
            counts["otherVenue"]+=1;continue
        try:
            if date_utc(row["trading date and time"])!=expected_date:
                counts["otherDate"]+=1;continue
        except ValueError:
            counts["invalidTime"]+=1;continue
        seen.add(isin)
    if not counts["reportRows"]:raise ValueError("empty report")
    return {"source":"LSEG TGHE post-trade","tradeUTCDate":expected_date,
            "rowCounts":dict(counts),"distinctISINs":len(seen),
            "targetISINs":len(target),"matchedTargetISINs":len(target & seen),
            "sessionCompletenessVerified":False,"pricePublicationAllowed":False,
            "pricesStored":False,"identitiesStored":False}

def validate_finazon(data,start,end):
    rows=data.get("data") if isinstance(data,dict) else None
    if not isinstance(rows,list) or not rows or len(rows)>1000:
        raise ValueError("unexpected time series response")
    seen=set()
    for r in rows:
        t=r["t"]
        if type(t) is not int or not start<=t<=end or t in seen:
            raise ValueError("timestamp_invalid_or_duplicate")
        seen.add(t)
        o,h,l,c,v=[r[k] for k in ("o","h","l","c","v")]
        if any(type(x) not in (int,float) or not math.isfinite(x) for x in (o,h,l,c,v)):
            raise ValueError("invalid_numeric_data")
        if not (0<l<=min(o,c)<=max(o,c)<=h and v>=0):
            raise ValueError("invalid_OHLCV")
    return {"validatedBars":len(rows),"earliestTimestamp":min(seen),"latestTimestamp":max(seen),
            "pricesStored":False,"pricePublicationAllowed":False,"officialCloseVerified":False}

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        return None

def get_finazon(symbol,start,end,key):
    if symbol not in TRIAL:raise ValueError("trial_symbols_only")
    url=FINAZON+"?"+urlencode({"ticker":symbol,"country":"US","interval":"1d","start_at":start,
                                "end_at":end,"page":0,"page_size":30})
    req=Request(url,headers={"Authorization":"apikey "+key,"Accept":"application/json",
                             "User-Agent":"StockwatchResearch/1.0"})
    with build_opener(NoRedirect()).open(req,timeout=30) as res:
        raw=res.read(1_000_001)
    if len(raw)>1_000_000:raise ValueError("response_limit")
    return json.loads(raw)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest="source",required=True)
    e=sub.add_parser("turquoise")
    e.add_argument("--file",type=Path,required=True)
    e.add_argument("--date",required=True)
    e.add_argument("--isin",action="append",default=[])
    e.add_argument("--authorized-use",action="store_true")
    u=sub.add_parser("finazon")
    u.add_argument("--start",type=int,required=True)
    u.add_argument("--end",type=int,required=True)
    u.add_argument("--authorized-trial",action="store_true")
    a=p.parse_args()
    if a.source=="turquoise":
        if not a.authorized_use:raise PermissionError("confirm authorized report use")
        if datetime.strptime(a.date,"%Y-%m-%d").date().isoformat()!=a.date:raise ValueError("invalid date")
        opener=gzip.open if a.file.suffix==".gz" else open
        with opener(a.file,"rt",encoding="utf-8-sig",newline="") as f:
            print(json.dumps(turquoise_audit(f,a.date,a.isin)))
    else:
        if not a.authorized_trial:raise PermissionError("confirm trial terms permit this use")
        if not 0<a.start<a.end<int(time.time()) or a.end-a.start>30*86400:
            raise ValueError("use completed historical interval of at most 30 days")
        key=os.environ.get("STOCKWATCH_FINAZON_API_KEY","").strip()
        if not key:raise ValueError("missing API key")
        for symbol in TRIAL:
            try:
                report=validate_finazon(get_finazon(symbol,a.start,a.end,key),a.start,a.end)
            except Exception as exc:
                print(json.dumps({"symbol":symbol,"status":"unavailable","errorType":type(exc).__name__}))
                return 1
            print(json.dumps({"symbol":symbol,"status":"validated_response",**report}))
            time.sleep(13)
    return 0

if __name__=="__main__":raise SystemExit(main())
