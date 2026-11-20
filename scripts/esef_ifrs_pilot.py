"""Bounded ESEF xBRL-JSON financial fact discovery; no production output."""
import json,hashlib,re,time
from collections import Counter,defaultdict
from datetime import date,datetime,timedelta
from decimal import Decimal,InvalidOperation
from urllib.parse import urlsplit,unquote
from urllib.request import Request,urlopen
from esef_filing_index import ROOT,URL,SOURCE,TERMS,targets,inspect

HOST="https://filings.xbrl.org"
METRICS={"Revenue":"duration","ProfitLoss":"duration","Assets":"instant","Liabilities":"instant","Equity":"instant","CashAndCashEquivalents":"instant","CashFlowsFromUsedInOperatingActivities":"duration","CashFlowsFromUsedInInvestingActivities":"duration","CashFlowsFromUsedInFinancingActivities":"duration"}
CORE={"concept","entity","period","unit"}
def qname(v,ns):
    if not isinstance(v,str) or ":" not in v:return None,None
    p,n=v.split(":",1)
    return ns.get(p),n
def json_path(p):
    if not isinstance(p,str) or not p.startswith("/") or p.startswith("//") or len(p)>2048:return None
    u=urlsplit(p)
    if u.netloc or u.scheme or u.query or u.fragment or "\\" in unquote(p) or any(x in ("..",".") for x in unquote(p).split("/")):return None
    if not u.path.endswith(".json"):return None
    return HOST+p
def cohort(index,wanted,limit=12):
    inspect(index,wanted)
    entities={e["id"]:e["attributes"]["identifier"] for e in index["included"] if e["type"]=="entity"}
    groups=defaultdict(list)
    for f in index["data"]:
        a=f["attributes"];lei=entities[f["relationships"]["entity"]["data"]["id"]]
        url=json_path(a.get("json_url"))
        if lei in wanted and url and type(a.get("error_count")) is int and a["error_count"]==0:
            groups[lei].append({"lei":lei,"id":f["id"],"period":a["period_end"],"country":a["country"],"url":url,"listingIds":sorted(wanted[lei])})
    # Deterministic, country-diverse pilot; never infer latest amendment from ID.
    countries=defaultdict(list)
    for lei,rows in sorted(groups.items()):
        rows.sort(key=lambda r:(r["period"],r["id"]),reverse=True)
        countries[rows[0]["country"]].append(rows[0])
    out=[]
    while len(out)<limit and any(countries.values()):
        for country in sorted(countries):
            if countries[country]:out.append(countries[country].pop(0))
            if len(out)==limit:break
    return out
def extract(doc,lei,period):
    info=doc["documentInfo"];ns=info["namespaces"];facts=doc["facts"]
    if info["documentType"]!="https://xbrl.org/2021/xbrl-json" or not isinstance(facts,dict) or len(facts)>200000:raise ValueError("invalid report envelope")
    if not isinstance(ns,dict):raise ValueError("invalid namespaces")
    end=(date.fromisoformat(period)+timedelta(days=1)).isoformat()+"T00:00:00"
    candidates=defaultdict(list);counts=Counter()
    for fid,f in facts.items():
        d=f["dimensions"];uri,concept=qname(d.get("concept"),ns)
        if concept not in METRICS or not isinstance(uri,str) or not re.fullmatch(r"https?://xbrl\.ifrs\.org/taxonomy/\d{4}-\d{2}-\d{2}/ifrs-full",uri):continue
        if set(d)!=CORE:counts["otherDimensions"]+=1;continue
        scheme,id_=qname(d["entity"],ns)
        if scheme not in ("http://standards.iso.org/iso/17442","https://standards.iso.org/iso/17442") or id_!=lei:counts["otherEntity"]+=1;continue
        unit,currency=qname(d["unit"],ns)
        if unit!="http://www.xbrl.org/2003/iso4217" or not re.fullmatch("[A-Z]{3}",currency or ""):counts["otherUnit"]+=1;continue
        p=d["period"]
        if not isinstance(p,str):counts["otherPeriod"]+=1;continue
        start=None
        if METRICS[concept]=="instant":
            if p!=end:counts["otherPeriod"]+=1;continue
        else:
            parts=p.split("/")
            if len(parts)!=2 or parts[1]!=end or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T00:00:00",parts[0]):counts["otherPeriod"]+=1;continue
            start=date.fromisoformat(parts[0][:10])
            if not 350<=(date.fromisoformat(end[:10])-start).days<=380:counts["otherPeriod"]+=1;continue
        raw=f.get("value");decimals=f.get("decimals")
        if not isinstance(raw,str) or len(raw)>100 or ("decimals" in f and type(decimals) is not int):counts["invalidValue"]+=1;continue
        try:value=Decimal(raw)
        except InvalidOperation:counts["invalidValue"]+=1;continue
        if not value.is_finite() or abs(value.adjusted())>50:counts["invalidValue"]+=1;continue
        candidates[concept].append({"factId":fid,"taxonomy":uri,"concept":concept,"currency":currency,"period":p,"value":raw,"decimals":decimals})
    accepted={}
    for name,rows in candidates.items():
        signatures={(Decimal(r["value"]),r["currency"],r["period"],r["taxonomy"],r["decimals"]) for r in rows}
        if len(signatures)!=1:counts["conflictingConcepts"]+=1;continue
        accepted[name]=sorted(rows,key=lambda r:r["factId"])[0]
    return accepted,dict(counts)
def get(url,bound):
    with urlopen(Request(url,headers={"User-Agent":"Nordl Stockwatch (+https://stocks.nordl.dev/)","Accept":"*/*"}),timeout=45) as r:
        if r.geturl()!=url:raise ValueError("unexpected redirect")
        raw=r.read(bound+1)
    if len(raw)>bound:raise ValueError("download bound")
    return raw
def main():
    raw=get(URL,64*1024**2);selected=cohort(json.loads(raw),targets(ROOT))
    if not selected:raise ValueError("no eligible filings")
    stats=[];metrics=Counter()
    for filing in selected:
        try:
            report=get(filing["url"],32*1024**2)
            found,rejected=extract(json.loads(report),filing["lei"],filing["period"])
            metrics.update(found.keys())
            stats.append({"filingId":filing["id"],"country":filing["country"],"sourceSha256":hashlib.sha256(report).hexdigest(),"metrics":sorted(found),"excluded":rejected,"status":"inspected"})
        except (OSError,ValueError,KeyError,TypeError) as exc:
            stats.append({"filingId":filing["id"],"country":filing["country"],"status":"failed","errorType":type(exc).__name__})
        time.sleep(.5)
    print("ESEF_IFRS_PILOT "+json.dumps({"indexSha256":hashlib.sha256(raw).hexdigest(),"selected":len(selected),"inspected":sum(r["status"]=="inspected" for r in stats),"metricCounts":dict(metrics),"candidateFacts":sum(metrics.values()),"financialFactsPublished":0,"retainedFacts":0,"consolidationVerified":False,"amendmentsResolved":False,"filings":stats},sort_keys=True))
    if not metrics or any(r["status"]=="failed" for r in stats):raise SystemExit(1)
if __name__=="__main__":main()
