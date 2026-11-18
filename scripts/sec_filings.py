"""Collect source-linked SEC filing metadata for the existing US research cohort.

No article/filing bodies, quote data, or inferred company events. The API's
reported acceptance timestamp and filer identity are retained. Refresh at most
once per UTC day; previous observations survive outages.
"""
from __future__ import annotations
import json, os, re, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
OUT="data/sec-filings.json"
DOCS="https://www.sec.gov/search-filings/edgar-application-programming-interfaces"
FORMS={"10-K":"Annual report","10-Q":"Quarterly report","8-K":"Current report",
       "20-F":"Annual report (foreign issuer)","40-F":"Annual report (Canadian issuer)",
       "6-K":"Foreign issuer report"}
EXCHANGES={"XNAS":"nasdaq","XNYS":"nyse"}
ACCESSION=re.compile(r"\d{10}-\d{2}-\d{6}")
CIK=re.compile(r"\d{10}")
MAX_BYTES=8_000_000

def iso(d):
    return d.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def parse_stamp(s):
    try:
        x=datetime.fromisoformat(str(s).replace("Z","+00:00"))
        return x.astimezone(timezone.utc) if x.tzinfo else None
    except (ValueError,TypeError):
        return None

def get(cik,agent):
    url=f"https://data.sec.gov/submissions/CIK{cik}.json"
    req=Request(url,headers={"User-Agent":agent,"Accept":"application/json"})
    with urlopen(req,timeout=10) as response:
        raw=response.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES: raise ValueError("response_too_large")
    return json.loads(raw)

def parse(seed,payload,now):
    cik=seed["cik"];symbol=seed["symbol"]
    if str(payload.get("cik","")).zfill(10)!=cik: raise ValueError("cik_mismatch")
    tickers=payload.get("tickers");exchanges=payload.get("exchanges")
    if not isinstance(tickers,list) or not isinstance(exchanges,list) or len(tickers)!=len(exchanges):
        raise ValueError("listing_identity_missing")
    if not any(t==symbol and str(e).casefold()==EXCHANGES.get(seed["mic"]) for t,e in zip(tickers,exchanges)):
        raise ValueError("ticker_exchange_mismatch")
    recent=payload.get("filings",{}).get("recent",{})
    fields=("accessionNumber","form","acceptanceDateTime","filingDate")
    if not all(isinstance(recent.get(k),list) for k in fields) or len({len(recent[k]) for k in fields})!=1:
        raise ValueError("filing_columns_invalid")
    rows={}
    for acc,form,accepted,filed in zip(*(recent[k] for k in fields)):
        if not isinstance(acc,str) or not ACCESSION.fullmatch(acc) or not isinstance(form,str):continue
        basic=form.removesuffix("/A")
        if basic not in FORMS:continue
        stamp=parse_stamp(accepted)
        if not stamp or not now-timedelta(days=180)<=stamp<=now:continue
        try:
            day=datetime.strptime(filed,"%Y-%m-%d").date()
        except (TypeError,ValueError):continue
        if day>now.date():continue
        title=FORMS[basic]+(" — amendment" if form.endswith("/A") else "")+f" ({form})"
        key=f"sec:{cik}:{symbol}:{acc}"
        rows[key]={"id":key,"ticker":symbol,"name":seed["name"],"sector":seed.get("sector",""),
            "type":"disclosure","headline":title,"english":None,"lang":"en","publisher":"SEC EDGAR",
            "url":f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc.replace('-','')}/{acc}-index.htm",
            "published":iso(stamp),"filingDate":filed,"form":form,"sourceFeed":"sec_edgar",
            "sourceIssuer":cik,"sourceAccession":acc,"match":"issuer_code","regulatory":True}
    return list(rows.values())

def build(root=ROOT,now=None,fetch=get,pause=time.sleep,agent=None):
    now=now or datetime.now(timezone.utc);target=root/OUT
    try:prior=json.loads(target.read_text(encoding="utf-8"))
    except (OSError,ValueError):prior={}
    # A single bounded collection per UTC day, independent of hourly scans.
    if str(prior.get("lastAttempt",""))[:10]==now.date().isoformat():return prior
    path=root/"data/us-equity-seed.json"
    if not path.exists():return prior
    seeds=json.loads(path.read_text(encoding="utf-8")).get("records",[])
    seeds=[s for s in seeds if isinstance(s,dict) and CIK.fullmatch(str(s.get("cik",""))) and
           s.get("mic") in EXCHANGES and s.get("symbol") and s.get("identityStatus")=="sec_ticker_exchange_association"][:50]
    old=prior.get("items",[])
    identities={(s["cik"],s["symbol"]) for s in seeds}
    records={x["id"]:x for x in old if x.get("id") and (x.get("sourceIssuer"),x.get("ticker")) in identities}
    status=dict(prior.get("issuers",{}))
    agent=agent if agent is not None else os.getenv("STOCKWATCH_SEC_USER_AGENT","").strip()
    allowed=bool(agent and "@" in agent)
    stopped=False
    for seed in seeds:
        cik=seed["cik"]
        old_status=status.get(cik,{})
        count=sum(x.get("sourceIssuer")==cik for x in records.values())
        row={**old_status,"ticker":seed["symbol"],"records":count,"lastAttempt":iso(now)}
        if not allowed or stopped:
            status[cik]={**row,"status":"awaiting_contact" if not allowed else "deferred"}
            continue
        try:
            new=parse(seed,fetch(cik,agent),now)
            for item in new:records[item["id"]]=item
            status[cik]={**row,"status":"ok","lastSuccess":iso(now),"records":sum(x.get("sourceIssuer")==cik for x in records.values())}
        except Exception as e:
            status[cik]={**row,"status":"error","errorType":type(e).__name__}
            # Respect access-control and rate-limit responses. Do not try alternate hosts.
            if isinstance(e,HTTPError) and e.code in (403,429):stopped=True
        pause(.35)
    result={"generated":iso(now),"lastAttempt":iso(now),"sourceUrl":DOCS,
            "notice":"SEC filing metadata only. Dates are accepted timestamps; forms are not interpreted as earnings, contracts or dividend events. No quote coverage implied.",
            "issuers":{k:v for k,v in status.items() if any(s["cik"]==k for s in seeds)},
            "items":sorted(records.values(),key=lambda x:(x["published"],x["id"]),reverse=True)}
    target.parent.mkdir(parents=True,exist_ok=True)
    tmp=target.with_suffix(".tmp")
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(target)
    print("SEC EDGAR:",len(result["items"]),"retained filing records;",
          sum(x.get("status")=="ok" for x in result["issuers"].values()),"successful issuers")
    return result

if __name__=="__main__":build()
