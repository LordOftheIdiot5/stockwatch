"""Retain scoped SEC as-filed transactions, without personal owner details or inferred trades."""
import json,hashlib,os,tempfile,zipfile,re
from datetime import datetime
from decimal import Decimal,InvalidOperation
from pathlib import Path
from collections import defaultdict
from urllib.request import Request,urlopen
from sec_insider_source import ROOT,SOURCE,URL,rows,inspect
def day(v):
    if not v:return None
    return datetime.strptime(v,"%d-%b-%Y").date().isoformat()
def amount(v):
    if not v:return None
    try:n=Decimal(v)
    except InvalidOperation:raise ValueError("invalid reported amount")
    if not n.is_finite() or n<0:raise ValueError("invalid reported amount")
    return str(n)
def extract(path,targets):
    counts=inspect(path,set(targets));filings={};out=defaultdict(list)
    with zipfile.ZipFile(path) as z:
        for r in rows(z,"SUBMISSION"):
            cik=r["ISSUERCIK"].zfill(10)
            if cik in targets:
                if "FILING_DATE" not in r:raise ValueError("filing date field missing")
                filed=day(r["FILING_DATE"])
                if not filed:raise ValueError("missing filing date")
                filings[r["ACCESSION_NUMBER"]]=(cik,r["DOCUMENT_TYPE"],filed)
        for table in ("NONDERIV_TRANS","DERIV_TRANS"):
            for r in rows(z,table):
                a=r["ACCESSION_NUMBER"]
                if a not in filings:continue
                cik,form,filed=filings[a]
                code=r["TRANS_CODE"].strip();direction=r["TRANS_ACQUIRED_DISP_CD"].strip()
                event={"accession":a,"table":table,"sourceRowKey":r[table+"_SK"],"form":form,"filingDate":filed,"transactionDate":day(r["TRANS_DATE"]),"code":code,"direction":direction,"amendment":form.endswith("/A"),"filingUrl":"https://www.sec.gov/Archives/edgar/data/"+str(int(cik))+"/"+a.replace("-","")+"/"+a+"-index.htm"}
                if table=="NONDERIV_TRANS":
                    event.update(securityTitle=r["SECURITY_TITLE"],reportedShares=amount(r["TRANS_SHARES"]),reportedPricePerShare=amount(r["TRANS_PRICEPERSHARE"]))
                out[cik].append(event)
    if sum(map(len,out.values()))!=sum(counts["counts"].get("matched:"+t,0) for t in ("NONDERIV_TRANS","DERIV_TRANS")):raise ValueError("coverage mismatch")
    return {c:sorted(out.get(c,[]),key=lambda r:(r["filingDate"],r["accession"],r["table"],r["sourceRowKey"])) for c in sorted(targets)}
def encode(d):return (json.dumps(d,sort_keys=True,ensure_ascii=False,indent=2)+chr(10)).encode()
def write(out,records,meta):
    out.mkdir(parents=True,exist_ok=True);index=[]
    for cik,events in records.items():
        content=encode({"schemaVersion":1,"issuerCIK":cik,"source":SOURCE,"archive":meta,"records":events,"notice":"As-filed evidence only; amendments unresolved, not unique economic transactions. Reported price/shares are not normalized trade values. No reporting-owner identities retained."})
        digest=hashlib.sha256(content).hexdigest();name=cik+"-"+digest+".json";p=out/name
        if p.exists() and p.read_bytes()!=content:raise ValueError("immutable evidence conflict")
        if not p.exists():p.write_bytes(content)
        index.append({"issuerCIK":cik,"records":len(events),"path":name,"sha256":digest})
    summary={"archive":meta,"issuers":len(index),"issuersWithRecords":sum(x["records"]>0 for x in index),"records":sum(x["records"] for x in index),"files":index,"publishedTransactions":0}
    tmp=out/"index.tmp";tmp.write_bytes(encode(summary));tmp.replace(out/"index.json")
    return summary
def main():
    agent=os.environ.get("STOCKWATCH_SEC_USER_AGENT","")
    if "@" not in agent:raise ValueError("SEC contact missing")
    seeds=json.loads((ROOT/"data/us-equity-seed.json").read_text())["records"];targets={r["cik"] for r in seeds}
    if not 1<=len(targets)<=50:raise ValueError("cohort bound")
    size=0;digest=hashlib.sha256()
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"archive.zip"
        with urlopen(Request(URL,headers={"User-Agent":agent,"Accept":"*/*"}),timeout=60) as r,p.open("wb") as f:
            if r.geturl()!=URL:raise ValueError("redirect")
            while chunk:=r.read(1024*1024):
                size+=len(chunk)
                if size>64*1024**2:raise ValueError("archive bound")
                digest.update(chunk);f.write(chunk)
        records=extract(p,targets)
    result=write(ROOT/"validation-artifacts/sec-insider",records,{"url":URL,"sha256":digest.hexdigest(),"bytes":size})
    print("SEC_INSIDER_EVIDENCE "+json.dumps({k:v for k,v in result.items() if k!="files"}))
if __name__=="__main__":main()
