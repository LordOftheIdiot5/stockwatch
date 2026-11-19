"""ESMA FIRDS official file-discovery preflight, not an instrument or price importer."""
from __future__ import annotations
import json,re
from collections import defaultdict
from datetime import date,datetime,timedelta,timezone
from urllib.parse import urlencode,urlsplit,urlunsplit
from urllib.request import Request,urlopen
REGISTER="https://registers.esma.europa.eu/solr/esma_registers_firds_files/select"
DOCS="https://www.esma.europa.eu/document/firds-instructions-access-and-download-full-and-delta-reference-data-files"
HOSTS={"firds.esma.europa.eu","registers.esma.europa.eu"}
NAME=re.compile(r"^(FULINS_E|DLTINS|FULCAN)_(\d{8})_(\d+)of(\d+)\.zip$")
PAGE=100
MAX_PAGES=30
def get(url):
    with urlopen(Request(url,headers={"User-Agent":"Nordl Stockwatch (https://stocks.nordl.dev/)","Accept":"application/json"}),timeout=30) as res:
        if urlsplit(res.geturl()).hostname!="registers.esma.europa.eu":raise ValueError("unexpected register host")
        raw=res.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:raise ValueError("register response too large")
    return json.loads(raw)
def discover(start,end,fetch=get):
    results=[];total=None
    for page in range(MAX_PAGES):
        offset=page*PAGE
        query=urlencode({"q":"*:*","fq":"publication_date:["+start.isoformat()+"T00:00:00Z TO "+end.isoformat()+"T23:59:59Z]","wt":"json","start":offset,"rows":PAGE,"sort":"file_name asc,id asc"})
        payload=fetch(REGISTER+"?"+query)
        if payload.get("responseHeader",{}).get("status")!=0:raise ValueError("register error")
        response=payload["response"];n=response["numFound"];docs=response["docs"]
        if type(n)!=int or n<0 or not isinstance(docs,list) or response.get("start")!=offset or len(docs)!=min(PAGE,max(0,n-offset)):raise ValueError("inconsistent page")
        if total is None:total=n
        if total!=n:raise ValueError("registry changed during pagination")
        results.extend(docs)
        if len(results)==total:return results
    raise ValueError("pagination limit exceeded")
def manifest(docs):
    groups=defaultdict(dict)
    for row in docs:
        name=row.get("file_name","")
        if not isinstance(name,str):raise ValueError("non-string filename")
        m=NAME.fullmatch(name)
        if not m:continue
        typ,stamp,p,t=m.groups();part,total=int(p),int(t)
        if not 1<=part<=total<=1000:raise ValueError("invalid part numbers")
        day=datetime.strptime(stamp,"%Y%m%d").date().isoformat()
        url=urlsplit(row["download_link"])
        if url.scheme not in ("http","https") or url.hostname not in HOSTS or url.username or url.password or url.port or url.query or url.fragment or url.path.split("/")[-1]!=name:raise ValueError("unexpected download link")
        secure=urlunsplit(("https",url.hostname,url.path,"",""))
        key=(typ,day)
        if part in groups[key]:raise ValueError("duplicate part")
        groups[key][part]={"name":name,"url":secure,"part":part,"expectedParts":total}
    out=[]
    for (typ,day),parts in sorted(groups.items()):
        totals={p["expectedParts"] for p in parts.values()}
        if len(totals)!=1:raise ValueError("inconsistent part counts")
        total=next(iter(totals))
        out.append({"type":typ,"date":day,"expectedParts":total,"foundParts":len(parts),"complete":set(parts)==set(range(1,total+1)),"files":[parts[k] for k in sorted(parts)]})
    return out
def probe(now=None,fetch=get):
    now=now or datetime.now(timezone.utc)
    end=now.date();start=end-timedelta(days=13);docs=discover(start,end,fetch)
    groups=manifest(docs);full=[g for g in groups if g["type"]=="FULINS_E"]
    if not full:raise ValueError("no equity full-file set in discovery window")
    latest=max(full,key=lambda g:g["date"])
    if not latest["complete"]:raise ValueError("latest equity full-file set incomplete")
    followups=[{"type":g["type"],"date":g["date"],"complete":g["complete"],"expectedParts":g["expectedParts"],"foundParts":g["foundParts"]} for g in groups if g["type"]!="FULINS_E" and g["date"]>=latest["date"]]
    result={"checkedAt":now.isoformat(),"source":DOCS,"windowStart":start.isoformat(),"windowEnd":end.isoformat(),"registryRows":len(docs),"latestEquityFullSet":latest,"subsequentDeltaAndCancellationSets":followups,"instrumentRecordsImported":0,"priceRecordsImported":0,"notice":"Manifest discovery only. A complete file manifest does not establish complete instrument coverage, ordered replay, file integrity or redistribution rights."}
    print("ESMA_FIRDS_MANIFEST "+json.dumps(result,sort_keys=True))
    return result
if __name__=="__main__":
    probe()
