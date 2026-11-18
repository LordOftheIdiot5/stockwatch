"""Nordic common-stock reference directory; no quote ingestion or ticker synthesis."""
import json, os, re, time, urllib.request, urllib.error
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT="data/instrument-directory.json"
SOURCE="https://www.openfigi.com/api/documentation"
URL="https://api.openfigi.com/v3/filter"
VENUES={"XOSL":"Oslo","XSTO":"Stockholm","XCSE":"Copenhagen","XHEL":"Helsinki",
        "XETR":"XETRA","XPAR":"Paris","XAMS":"Amsterdam","XLON":"London"}
EXPANSION_VENUES={"XETR","XPAR","XAMS","XLON"}
MAX_PAGES=15
def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def figi(v):
    return v if isinstance(v,str) and re.fullmatch(r"[A-Z0-9]{12}",v) else None
def normalize(row,mic):
    if not isinstance(row,dict) or row.get("marketSector")!="Equity" or row.get("securityType")!="Common Stock":
        return None
    code=figi(row.get("figi"))
    name=str(row.get("name") or "").strip()
    symbol=str(row.get("ticker") or "").strip()
    if not code or not name or not symbol or len(name)>250 or len(symbol)>80:
        return None
    return {"figi":code,"name":name,"ticker":symbol,"mic":mic,"venue":VENUES[mic],
            "shareClassFIGI":figi(row.get("shareClassFIGI")),
            "compositeFIGI":figi(row.get("compositeFIGI")),
            "securityType":"Common Stock","source":"OpenFIGI","quoteStatus":"not_connected"}
def request(payload,key):
    headers={"Content-Type":"application/json","User-Agent":"StockwatchResearch/1.0 (+https://stocks.nordl.dev)","X-OPENFIGI-APIKEY":key}
    for attempt in range(3):
        try:
            req=urllib.request.Request(URL,data=json.dumps(payload).encode(),headers=headers,method="POST")
            with urllib.request.urlopen(req,timeout=25) as res:
                raw=res.read(1500001)
                if len(raw)>1500000: raise ValueError("response_too_large")
            obj=json.loads(raw)
            if not isinstance(obj,dict) or not isinstance(obj.get("data"),list): raise ValueError("invalid_filter_response")
            return obj
        except urllib.error.HTTPError as e:
            if e.code not in (429,500,502,503,504) or attempt==2: raise
            time.sleep(65 if e.code==429 else 5*(attempt+1))
    raise RuntimeError("unreachable")
def collect(mic,key,fetch=request,pause=time.sleep):
    token=None
    seen=set()
    rows={}
    for page in range(8 if mic in EXPANSION_VENUES else MAX_PAGES):
        payload={"micCode":mic,"marketSecDes":"Equity","securityType":"Common Stock"}
        if token: payload["start"]=token
        data=fetch(payload,key)
        for row in data["data"]:
            x=normalize(row,mic)
            if x: rows[x["figi"]]=x
        token=data.get("next")
        if not token:
            if not rows: raise ValueError("empty_venue")
            return list(rows.values()),True
        if not isinstance(token,str) or token in seen: raise ValueError("invalid_cursor")
        seen.add(token);pause(3.4)
    if not rows: raise ValueError("empty_venue")
    return list(rows.values()),False
def build(root=ROOT,fetch=request,pause=time.sleep):
    target=root/OUT
    try: prior=json.loads(target.read_text())
    except (OSError,ValueError): prior={}
    old=prior.get("records",[])
    key=os.getenv("STOCKWATCH_OPENFIGI_KEY","").strip()
    records=[];status={}
    for mic in VENUES:
        previous=[r for r in old if r.get("mic")==mic]
        if not key:
            records.extend(previous);status[mic]={"status":"awaiting_key","records":len(previous)}
            continue
        try:
            rows,complete=collect(mic,key,fetch,pause)
            if not complete:
                # Retain past records on bounded partial traversal, disclose incompleteness.
                rows=list({r["figi"]:r for r in previous+rows}.values())
            records.extend(rows);status[mic]={"status":"ok" if complete else "partial","records":len(rows),"complete":complete,"checkedAt":stamp()}
        except Exception as e:
            records.extend(previous);status[mic]={"status":"error","records":len(previous),"errorType":type(e).__name__}
        pause(3.4)
    records=sorted(records,key=lambda r:(r["mic"],r["name"],r["figi"]))
    result={"generated":stamp(),"sourceUrl":SOURCE,"notice":"Reference records only; not independently verified primary listings or monitored prices. Per-venue results may overlap at issuer or share-class level.","venues":status,"records":records}
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    path=root/"data/dataset-catalog.json"
    if path.exists():
        catalog=json.loads(path.read_text());catalog["datasets"]=[x for x in catalog.get("datasets",[]) if x.get("path")!=OUT]+[{"name":"European common-stock instrument directory","path":OUT,"records":len(records),"license":"OpenFIGI open symbology and associated metadata; no quote rights implied"}];path.write_text(json.dumps(catalog,indent=2,ensure_ascii=False)+"\n")
    print("OpenFIGI directory:",len(records),"venue reference records;",{m:v["status"] for m,v in status.items()})
    return result
if __name__=="__main__": build()
