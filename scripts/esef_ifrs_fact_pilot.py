"""Strict as-filed IFRS fact candidates for the Mowi 2025 pilot, not a financial statement."""
import hashlib,json,re
from collections import defaultdict
from datetime import date,datetime,timedelta
from decimal import Decimal,InvalidOperation
from urllib.request import Request,urlopen
from esef_filing_index import ROOT,targets
LEI="549300W1OGQF5LZIH349"
END="2025-12-31"
URL="https://filings.xbrl.org/549300W1OGQF5LZIH349/2025-12-31/ESEF/NO/0/mowi-2025-12-31-1-en.json"
INSTANT={"Assets","Liabilities","Equity","CashAndCashEquivalents"}
DURATION={"Revenue","ProfitLoss","ProfitLossFromOperatingActivities","CashFlowsFromUsedInOperatingActivities","CashFlowsFromUsedInInvestingActivities","CashFlowsFromUsedInFinancingActivities"}
def qname(s,ns):
    if not isinstance(s,str) or s.count(":")!=1:return None,None
    p,v=s.split(":");return ns.get(p),v
def midnight(s):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T00:00:00",s):raise ValueError("unsupported reporting timestamp")
    return datetime.fromisoformat(s).date()
def inspect(d,lei=LEI,end=END):
    info=d["documentInfo"];ns=info["namespaces"];facts=d["facts"]
    if info.get("documentType")!="https://xbrl.org/2021/xbrl-json" or not isinstance(facts,dict) or not 1<=len(facts)<=100000:raise ValueError("unsupported document")
    boundary=date.fromisoformat(end)+timedelta(days=1)
    groups=defaultdict(list)
    for fid,f in facts.items():
        dim=f.get("dimensions",{})
        uri,concept=qname(dim.get("concept"),ns)
        if not isinstance(uri,str) or not re.fullmatch(r"https?://xbrl.ifrs.org/taxonomy/\d{4}-\d{2}-\d{2}/ifrs-full",uri) or concept not in INSTANT|DURATION:continue
        if set(dim)!={"concept","entity","period","unit"}:continue
        euri,eid=qname(dim["entity"],ns)
        if euri not in {"http://standards.iso.org/iso/17442","https://standards.iso.org/iso/17442"} or eid!=lei:continue
        uuri,currency=qname(dim["unit"],ns)
        if uuri!="http://www.xbrl.org/2003/iso4217" or not re.fullmatch("[A-Z]{3}",currency or ""):continue
        period=dim["period"]
        try:
            parts=[midnight(p) for p in period.split("/")]
        except (ValueError,AttributeError):continue
        if parts[-1]!=boundary:continue
        if concept in INSTANT and len(parts)!=1:continue
        if concept in DURATION and (len(parts)!=2 or not 350<=(parts[1]-parts[0]).days<=380):continue
        raw=f.get("value")
        if not isinstance(raw,str) or len(raw)>80:continue
        try:value=Decimal(raw)
        except InvalidOperation:continue
        if not value.is_finite() or abs(value)>Decimal("1e25"):continue
        decimals=f.get("decimals")
        if decimals is not None and (type(decimals)!=int or abs(decimals)>20):continue
        # Keep duplicates as evidence; no preference by precision or language.
        groups[(uri,concept,currency,period)].append({"factId":fid,"value":raw,"decimals":decimals})
    rows=[]
    for (uri,concept,currency,period),items in sorted(groups.items()):
        values={Decimal(x["value"]) for x in items}
        rows.append({"taxonomy":uri,"concept":concept,"currency":currency,"period":period,"status":"candidate" if len(values)==1 else "conflicting","facts":items})
    if not rows:raise ValueError("no qualifying IFRS facts")
    return rows
def main():
    if LEI not in targets(ROOT):raise ValueError("issuer outside reviewed cohort")
    with urlopen(Request(URL,headers={"User-Agent":"Nordl Stockwatch (+https://stocks.nordl.dev/)","Accept":"*/*"}),timeout=60) as r:
        if r.geturl()!=URL:raise ValueError("unexpected redirect")
        raw=r.read(32*1024**2+1)
    if len(raw)>32*1024**2:raise ValueError("report bound")
    rows=inspect(json.loads(raw))
    # Diagnostics only. Do not publish raw facts or infer consolidation.
    print("IFRS_FACT_PILOT "+json.dumps({"issuerLEI":LEI,"periodEnd":END,"reportUrl":URL,"sha256":hashlib.sha256(raw).hexdigest(),"candidateContexts":sum(x["status"]=="candidate" for x in rows),"conflictingContexts":sum(x["status"]=="conflicting" for x in rows),"concepts":sorted({x["concept"] for x in rows}),"currencies":sorted({x["currency"] for x in rows}),"publishedFacts":0,"consolidationVerified":False}))
if __name__=="__main__":main()
