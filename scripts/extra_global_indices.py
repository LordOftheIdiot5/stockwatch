"""Official additional daily Taiwan benchmarks, independent retained snapshots."""
import argparse,json,math,re
from datetime import datetime,timezone,date
from pathlib import Path
from urllib.request import Request,urlopen
from global_indices import ROOT,LICENSE
SOURCES={
 "tpex":{"key":"tpex:TPEx","name":"TPEx","market":"Taipei Exchange","provider":"Taipei Exchange / Financial Supervisory Commission","endpoint":"https://www.tpex.org.tw/openapi/v1/tpex_index","sourceUrl":"https://data.gov.tw/dataset/11391","dateFormat":"gregorian","closeField":"Close","changeField":"Change"},
 "formosa":{"key":"twse:FORMOSA","name":"Formosa Index","market":"Taiwan combined markets","provider":"Taiwan Stock Exchange / Financial Supervisory Commission","endpoint":"https://openapi.twse.com.tw/v1/indicesReport/FRMSA","sourceUrl":"https://data.gov.tw/dataset/11669","dateFormat":"roc","closeField":"FormosaIndex","changeField":None}
}
def number(s):
    n=float(str(s).replace(",",""))
    if not math.isfinite(n):raise ValueError("nonfinite observation")
    return n
def parse(spec,raw,today,previous=None):
    if not isinstance(raw,list) or not 1<=len(raw)<=400:raise ValueError("invalid payload")
    history={x["date"]:x for x in previous or []};fresh={}
    for row in raw:
        rawdate=str(row["Date"])
        if spec["dateFormat"]=="roc":
            if not re.fullmatch("[0-9]{7}",rawdate):raise ValueError("invalid ROC date")
            rawdate=str(int(rawdate[:3])+1911)+rawdate[3:]
        if not re.fullmatch("[0-9]{8}",rawdate):raise ValueError("invalid date")
        d=datetime.strptime(rawdate,"%Y%m%d").date().isoformat()
        if d>today.isoformat():raise ValueError("future observation")
        value=number(row[spec["closeField"]])
        change=number(row[spec["changeField"]]) if spec["changeField"] else None
        if value<=0 or (change is not None and value-change<=0):raise ValueError("invalid close")
        item=(value,change)
        if d in fresh and fresh[d]!=item:raise ValueError("conflicting close")
        fresh[d]=item
    if history and max(fresh)<max(history):raise ValueError("source regressed")
    values={k:(v["close"],v.get("changePoints")) for k,v in history.items()}
    values.update(fresh)
    out=[];prior=None
    for d,(value,change) in sorted(values.items()):
        # Formosa reports levels only. Do not infer a cross-gap day change.
        if spec["changeField"] is None:
            if prior and (date.fromisoformat(d)-date.fromisoformat(prior[0])).days<=4:
                change=round(value-prior[1],6)
            else:change=None
        pct=round(100*change/(value-change),6) if change is not None and value-change>0 else None
        out.append({"date":d,"close":value,"changePoints":change,"changePct":pct})
        prior=(d,value)
    return out
def fetch(spec):
    url=spec["endpoint"]
    with urlopen(Request(url,headers={"User-Agent":"Nordl Stockwatch (+https://stocks.nordl.dev/)","Accept":"application/json"}),timeout=30) as r:
        if r.geturl()!=url:raise ValueError("unexpected redirect")
        raw=r.read(1000001)
    if len(raw)>1000000:raise ValueError("response too large")
    return json.loads(raw)
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8");tmp.replace(path)
def build(root=ROOT,now=None,get=fetch,probe=False):
    now=now or datetime.now(timezone.utc);today=now.date();stamp=now.isoformat();results={};failures=[]
    for slug,spec in SOURCES.items():
        path=root/"data"/("global-index-"+slug+".json")
        old=json.loads(path.read_text()) if path.exists() else {}
        if not probe and old.get("history") and (now.hour<6 or (old.get("status")=="ok" and old.get("latest",{}).get("date")==today.isoformat())):
            results[slug]=old;continue
        metadata={k:v for k,v in spec.items() if k not in ("dateFormat","closeField","changeField")}
        base={"schemaVersion":1,**metadata,"license":"Taiwan Open Government Data License 1.0; attribution required","licenseUrl":LICENSE,"notice":"Dated official closing observations. Formosa changes are calculated from adjacent retained source observations when the date gap is at most four calendar days; not live quotes."}
        try:
            history=parse(spec,get(spec),today,old.get("history"))
            out={**base,"status":"ok","lastAttempt":stamp,"lastSuccessAt":stamp,"history":history,"latest":history[-1]}
        except Exception as e:
            failures.append(slug)
            out={**base,**old,"status":"retained_after_error" if old.get("history") else "unavailable","lastAttempt":stamp,"errorType":type(e).__name__}
        if not probe:save(path,out)
        results[slug]=out
        print("EXTRA_GLOBAL_INDEX "+json.dumps({"key":spec["key"],"status":out["status"],"latest":out.get("latest"),"observations":len(out.get("history",[]))}))
    if failures:raise RuntimeError("index source failures: "+",".join(failures))
    return results
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--probe",action="store_true");a=p.parse_args();build(probe=a.probe)
