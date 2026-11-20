"""Official Taiwan daily market benchmark; no scraped or unlicensed indices."""
import argparse,json,math,re
from datetime import date,datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
URL="https://openapi.twse.com.tw/v1/exchangeReport/FMTQIK"
SOURCE="https://data.gov.tw/en/datasets/11672"
LICENSE="https://data.gov.tw/en/license"
def parse(raw,today):
    if not isinstance(raw,list) or not raw or len(raw)>400:raise ValueError("invalid payload")
    out={}
    for row in raw:
        d=str(row["Date"])
        if not re.fullmatch(r"\d{7}",d):raise ValueError("invalid ROC date")
        day=date(int(d[:3])+1911,int(d[3:5]),int(d[5:])).isoformat()
        if day>today.isoformat():raise ValueError("future observation")
        value=float(str(row["TAIEX"]).replace(",",""));change=float(str(row["Change"]).replace(",",""))
        if not all(math.isfinite(x) for x in (value,change)) or value<=0 or value-change<=0:raise ValueError("invalid index")
        item={"date":day,"close":value,"changePoints":change,"changePct":round(100*change/(value-change),6)}
        if day in out and out[day]!=item:raise ValueError("conflicting close")
        out[day]=item
    return sorted(out.values(),key=lambda x:x["date"])
def fetch():
    req=Request(URL,headers={"User-Agent":"Nordl Stockwatch (+https://stocks.nordl.dev/)","Accept":"application/json"})
    with urlopen(req,timeout=30) as r:
        if r.geturl()!=URL:raise ValueError("unexpected redirect")
        raw=r.read(1000001)
    if len(raw)>1000000:raise ValueError("size limit")
    return json.loads(raw)
def build(root=ROOT,now=None,get=fetch,probe=False):
    now=now or datetime.now(timezone.utc);stamp=now.isoformat();path=root/"data/global-indices-v1.json"
    old=json.loads(path.read_text()) if path.exists() else {}
    # Taiwan normally closes at 05:30 UTC. Avoid hourly repeat requests after successful daily collection.
    if not probe and now.hour<6 and old.get("history"):return old
    if not probe and old.get("lastSuccessAt","")[:10]==now.date().isoformat() and old.get("latest",{}).get("date")==now.date().isoformat():return old
    try:
        points=parse(get(),now.date());previous={x["date"]:x for x in old.get("history",[])}
        if previous and points[-1]["date"]<max(previous):raise ValueError("source regressed")
        previous.update({x["date"]:x for x in points});history=sorted(previous.values(),key=lambda r:r["date"])
        out={"schemaVersion":1,"key":"twse:TAIEX","market":"Taiwan","name":"TAIEX","provider":"Taiwan Stock Exchange / Financial Supervisory Commission","sourceUrl":SOURCE,"endpoint":URL,"license":"Taiwan Open Government Data License 1.0; attribution required","licenseUrl":LICENSE,"status":"ok","lastSuccessAt":stamp,"lastAttempt":stamp,"history":history,"latest":history[-1],"notice":"Completed-session index observations; not live quotes. Daily percentage derived from source close and reported point change. Session date is Taiwan local date."}
    except Exception as e:
        out={**old,"schemaVersion":1,"key":"twse:TAIEX","status":"retained_after_error" if old.get("history") else "unavailable","lastAttempt":stamp,"errorType":type(e).__name__}
        if not probe:
            path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n");tmp.replace(path)
        raise
    if not probe:
        path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n");tmp.replace(path)
    print("GLOBAL_INDEX "+json.dumps({"status":out["status"],"latest":out["latest"],"observations":len(out["history"])}));return out
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--probe",action="store_true");a=p.parse_args();build(probe=a.probe)
