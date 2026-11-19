"""SEC Company Facts: selected as-filed issuer-level XBRL observations, not quotes."""
from __future__ import annotations
import json, os, time, math, re
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from sec_filings import CIK, EXCHANGES, ACCESSION, iso
ROOT=Path(__file__).resolve().parents[1]
DOCS="https://www.sec.gov/search-filings/edgar-application-programming-interfaces"
TAGS={"RevenueFromContractWithCustomerExcludingAssessedTax":"USD","Revenues":"USD","SalesRevenueNet":"USD","NetIncomeLoss":"USD","OperatingIncomeLoss":"USD","Assets":"USD","Liabilities":"USD","StockholdersEquity":"USD","CashAndCashEquivalentsAtCarryingValue":"USD","NetCashProvidedByUsedInOperatingActivities":"USD","PaymentsToAcquirePropertyPlantAndEquipment":"USD","EarningsPerShareDiluted":"USD/shares","CommonStockSharesOutstanding":"shares","LongTermDebtCurrent":"USD","LongTermDebtNoncurrent":"USD"}
FORMS={"10-K","10-Q","20-F","40-F","10-K/A","10-Q/A","20-F/A","40-F/A"}
MAX_BYTES=32*1024*1024
def day(s):
    try:
        d=date.fromisoformat(s)
        return d if d.isoformat()==s else None
    except (TypeError,ValueError):return None
def get(cik,agent):
    url=f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    with urlopen(Request(url,headers={"User-Agent":agent,"Accept":"application/json"}),timeout=15) as res:
        if res.geturl()!=url:raise ValueError("unexpected_redirect")
        raw=res.read(MAX_BYTES+1)
    if len(raw)>MAX_BYTES:raise ValueError("response_too_large")
    return json.loads(raw)
def parse(cik,payload,today):
    if str(payload.get("cik","")).zfill(10)!=cik:raise ValueError("cik_mismatch")
    taxonomy=payload.get("facts",{}).get("us-gaap",{})
    records={}
    for tag,unit in TAGS.items():
        for x in taxonomy.get(tag,{}).get("units",{}).get(unit,[]):
            end, filed=day(x.get("end")),day(x.get("filed"))
            start=day(x.get("start")) if x.get("start") else None
            acc=x.get("accn","");value=x.get("val")
            if not end or not filed or not end<=filed<=today or end<today-timedelta(days=365*6):continue
            if x.get("start") and (not start or start>end):continue
            if x.get("form") not in FORMS or not isinstance(acc,str) or not ACCESSION.fullmatch(acc):continue
            if type(value) not in (int,float) or not math.isfinite(value):continue
            key="|".join([tag,unit,str(start or ""),str(end),acc])
            row={"tag":tag,"unit":unit,"start":str(start) if start else None,"end":str(end),"filed":str(filed),"accession":acc,"form":x["form"],"value":value,"sourceUrl":f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-','')}/{acc}-index.htm"}
            if key in records and records[key]!=row:raise ValueError("conflicting_fact")
            records[key]=row
    return records
def build(root=ROOT,now=None,fetch=get,pause=time.sleep,agent=None):
    now=now or datetime.now(timezone.utc);out=root/"data/sec-companyfacts";out.mkdir(parents=True,exist_ok=True)
    def read(p,default):
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
    def write(p,data):
        tmp=p.with_suffix(".tmp");tmp.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8");tmp.replace(p)
    idx=out/"index.json";prior=read(idx,{})
    if str(prior.get("lastAttempt",""))[:10]==now.date().isoformat():return prior
    seeds=read(root/"data/us-equity-seed.json",{})["records"]
    ids={}
    for seed in seeds:
        if CIK.fullmatch(str(seed.get("cik",""))) and seed.get("mic") in EXCHANGES and seed.get("identityStatus")=="sec_ticker_exchange_association":
            ids.setdefault(seed["cik"],[]).append(seed["id"])
    agent=(agent if agent is not None else os.environ.get("STOCKWATCH_SEC_USER_AGENT","")).strip()
    allowed="@" in agent;stopped=False;status={}
    for cik,listings in list(ids.items())[:50]:
        dest=out/(cik+".json");old=read(dest,{});records=old.get("records",{})
        last=old.get("lastSuccess")
        state="awaiting_contact" if not allowed else "deferred" if stopped else "error"
        if allowed and not stopped:
            try:
                new=parse(cik,fetch(cik,agent),now.date())
                if not new:raise ValueError("no_selected_facts")
                if any(k in records and records[k]!=v for k,v in new.items()):raise ValueError("prior_fact_conflict")
                records={**records,**new};last=iso(now)
                write(dest,{"cik":cik,"taxonomy":"us-gaap","lastSuccess":last,"records":records,"notice":"As-filed facts; multiple fiscal periods and filing revisions retained. Not normalized standalone quarterly results."})
                state="ok"
            except Exception as e:
                state="error:"+type(e).__name__
                if isinstance(e,HTTPError) and e.code in (403,429):stopped=True
            pause(.4)
        status[cik]={"listingIds":listings,"status":state,"lastSuccess":last,"records":len(records),"path":"data/sec-companyfacts/"+cik+".json" if records else None}
    result={"schemaVersion":1,"lastAttempt":iso(now),"sourceUrl":DOCS,"issuers":status,"notice":"Selected issuer-level US-GAAP facts in reported units; no inferred quarters, values or price data. Initial six-year lookback; prior records preserved."}
    write(idx,result)
    print("SEC_COMPANYFACTS "+json.dumps({"issuers":len(status),"successful":sum(x["status"]=="ok" for x in status.values()),"retainedFacts":sum(x["records"] for x in status.values())}))
    return result
if __name__=="__main__":build()
