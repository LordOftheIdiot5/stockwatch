"""Refresh explicit research targets using OpenFIGI, with dated mapping evidence.

No prices are fetched. A single matching record is evidence, not a verified
legal entity identity or confirmation of primary listing. Prior mapping evidence
is retained when a provider request fails or returns ambiguous results.
"""
from __future__ import annotations
import json,os,re,time,urllib.request,urllib.error
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT="data/research-coverage.json"
URL="https://api.openfigi.com/v3/mapping"
SOURCE="https://www.openfigi.com/api/documentation"
def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def load(path,default):
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError): return default
def valid_figi(x):
    return isinstance(x,str) and bool(re.fullmatch(r"[A-Z0-9]{12}",x))
def job(t):
    return {"idType":"ID_ISIN" if t.get("isin") else "TICKER","idValue":t.get("isin") or t["symbol"],"micCode":t["mic"],"marketSecDes":"Equity"}
def norm(v):
    return re.sub(r"[\s./-]+","",str(v or "").upper())
def candidate(t,reply):
    found={}
    for x in reply.get("data",[]) or []:
        if not isinstance(x,dict) or x.get("marketSector")!="Equity" or not valid_figi(x.get("figi")):continue
        if norm(x.get("ticker"))!=norm(t["symbol"]) and not t.get("isin"):continue
        found[x["figi"]]=x
    if not found:return "unresolved",None
    if len(found)!=1:return "ambiguous",None
    x=next(iter(found.values()))
    return "candidate",{"figi":x["figi"],"shareClassFIGI":x.get("shareClassFIGI") if valid_figi(x.get("shareClassFIGI")) else None,"compositeFIGI":x.get("compositeFIGI") if valid_figi(x.get("compositeFIGI")) else None,"providerName":x.get("name"),"providerTicker":x.get("ticker"),"securityType":x.get("securityType"),"method":"ISIN + MIC" if t.get("isin") else "Ticker + MIC","sourceUrl":SOURCE,"verified":False}
def request(jobs,key):
    req=urllib.request.Request(URL,data=json.dumps(jobs).encode(),headers={"Content-Type":"application/json","X-OPENFIGI-APIKEY":key,"User-Agent":"StockwatchResearch/1.0 (+https://stocks.nordl.dev)"},method="POST")
    for i in range(3):
        try:
            with urllib.request.urlopen(req,timeout=30) as r:
                payload=r.read(2000001)
            if len(payload)>2000000:raise ValueError("response too large")
            result=json.loads(payload)
            if not isinstance(result,list) or len(result)!=len(jobs) or any(not isinstance(x,dict) for x in result):raise ValueError("invalid mapping response")
            return result
        except urllib.error.HTTPError as e:
            if e.code not in (429,500,502,503,504) or i==2:raise
            time.sleep(65 if e.code==429 else 5*(i+1))
def build(root=ROOT,fetch=request,key=None):
    targets=load(root/"data/research-targets.json",{})["targets"]
    old=load(root/OUT,{});past={r["id"]:r for r in old.get("records",[])}
    key=os.getenv("STOCKWATCH_OPENFIGI_KEY","").strip() if key is None else key
    replies=None
    if key:
        try:replies=fetch([job(t) for t in targets],key)
        except Exception:pass
    now=stamp();records=[]
    for i,t in enumerate(targets):
        p=past.get(t["id"],{});history=list(p.get("mappingHistory",[]));last=p.get("lastCandidate")
        status,mapping=candidate(t,replies[i]) if replies is not None else ("source_unavailable" if key else "awaiting_key",None)
        if mapping:
            if not history or history[-1].get("mapping")!=mapping or history[-1].get("status")!="candidate":
                history.append({"observedAt":now,"status":"candidate","mapping":mapping})
            last=mapping
        elif replies is not None and (not history or history[-1].get("status")!=status):
            history.append({"observedAt":now,"status":status,"mapping":None})
        records.append({**t,"quoteStatus":"not_connected","mappingStatus":status,"currentCandidate":mapping,"lastCandidate":last,"lastChecked":now if replies is not None else p.get("lastChecked"),"mappingHistory":history})
    result={"generated":now,"sourceUrl":SOURCE,"notice":"Mapping history records changes observed by Stockwatch, not historical FIGI assignments before collection began. Current and prior candidates are unverified; no price feed or corporate relationship is implied.","records":records}
    dest=root/OUT;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    catalog=root/"data/dataset-catalog.json"
    if catalog.exists():
        d=load(catalog,{"datasets":[]});d["datasets"]=[x for x in d.get("datasets",[]) if x.get("path")!=OUT]+[{"name":"European research targets and observed OpenFIGI mapping evidence","path":OUT,"records":len(records),"license":"OpenFIGI reference metadata and Stockwatch research selections; no market price rights implied"}];catalog.write_text(json.dumps(d,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Research coverage:",len(records),"targets;",sum(r["mappingStatus"]=="candidate" for r in records),"single candidates")
    return result
if __name__=="__main__":build()
