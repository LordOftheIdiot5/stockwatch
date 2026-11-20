"""Read-only SEC 13F archive source and accession join check."""
import csv,hashlib,io,json,os,tempfile,zipfile
from collections import Counter
from datetime import datetime,date
from pathlib import Path
from urllib.request import Request,urlopen
URL="https://www.sec.gov/files/datastandardsinnovation/data/form-13f-data-sets/01jun2026-31aug2026_form13f.zip"
SOURCE="https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets"
REQUIRED={"SUBMISSION":"ACCESSION_NUMBER FILING_DATE SUBMISSIONTYPE CIK PERIODOFREPORT","COVERPAGE":"ACCESSION_NUMBER AMENDMENTTYPE FILINGMANAGER_NAME REPORTTYPE","INFOTABLE":"ACCESSION_NUMBER INFOTABLE_SK CUSIP FIGI VALUE SSHPRNAMT SSHPRNAMTTYPE PUTCALL OTHERMANAGER"}
def unit(day):
    return "USD" if day>=date(2023,1,3) else "thousand USD"
def rows(z,table):
    files=[f for f in z.infolist() if f.filename.upper()==table+".TSV"]
    if len(files)!=1:raise ValueError("missing or duplicate table "+table)
    with z.open(files[0]) as b,io.TextIOWrapper(b,encoding="utf-8-sig",newline="") as f:
        r=csv.DictReader(f,delimiter=chr(9),quoting=csv.QUOTE_NONE)
        if not set(REQUIRED[table].split())<=set(r.fieldnames or []):raise ValueError("unexpected header")
        for row in r:
            if None in row or None in row.values():raise ValueError("malformed row")
            yield row
def inspect(path):
    sub={};cover=set();counts=Counter();forms=Counter();amend=Counter();units=Counter();periods=Counter();managers=set()
    with zipfile.ZipFile(path) as z:
        if len(z.infolist())>30 or sum(f.file_size for f in z.infolist())>3*1024**3:raise ValueError("archive exceeds bound")
        for r in rows(z,"SUBMISSION"):
            a=r["ACCESSION_NUMBER"];form=r["SUBMISSIONTYPE"]
            if a in sub or form not in ("13F-HR","13F-HR/A","13F-NT","13F-NT/A"):raise ValueError("invalid submission")
            d=datetime.strptime(r["FILING_DATE"],"%d-%b-%Y").date()
            p=datetime.strptime(r["PERIODOFREPORT"],"%d-%b-%Y").date()
            if p>d:raise ValueError("report date after filing")
            sub[a]=(d,form);forms[form]+=1;periods[p.isoformat()]+=1;managers.add(r["CIK"])
            if len(sub)>100000:raise ValueError("submission bound")
        for r in rows(z,"COVERPAGE"):
            a=r["ACCESSION_NUMBER"]
            if a not in sub or a in cover:raise ValueError("cover join")
            cover.add(a)
            if sub[a][1].endswith("/A"):amend[r["AMENDMENTTYPE"] or "unspecified"]+=1
        for r in rows(z,"INFOTABLE"):
            a=r["ACCESSION_NUMBER"];counts["holdingRows"]+=1
            if counts["holdingRows"]>10000000:raise ValueError("holding bound")
            if a not in sub or a not in cover:raise ValueError("orphan holding")
            if sub[a][1] not in ("13F-HR","13F-HR/A"):raise ValueError("notice holdings")
            units[unit(sub[a][0])]+=1
            option=r["PUTCALL"].strip().upper();typ=r["SSHPRNAMTTYPE"].strip().upper()
            counts["optionRows" if option in ("PUT","CALL") else "sharesWithoutOption" if typ=="SH" and not option else "principalRows" if typ=="PRN" and not option else "otherRows"]+=1
            if r["FIGI"].strip():counts["figiRows"]+=1
            if r["OTHERMANAGER"].strip():counts["otherManagerRows"]+=1
    if not sub or not counts["holdingRows"]:raise ValueError("empty archive")
    return {"submissions":len(sub),"coverpages":len(cover),"managerCIKs":len(managers),"forms":dict(forms),"amendments":dict(amend),"reportPeriods":dict(periods),"counts":dict(counts),"valueUnits":dict(units),"companyHoldingsPublished":0}
def main():
    agent=os.environ.get("STOCKWATCH_SEC_USER_AGENT","")
    if "@" not in agent:raise ValueError("SEC contact missing")
    digest=hashlib.sha256();size=0
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"source.zip"
        with urlopen(Request(URL,headers={"User-Agent":agent,"Accept":"*/*"}),timeout=90) as r,p.open("wb") as f:
            if r.geturl()!=URL:raise ValueError("redirect")
            while chunk:=r.read(1024*1024):
                size+=len(chunk)
                if size>200*1024*1024:raise ValueError("compressed bound")
                digest.update(chunk);f.write(chunk)
        result=inspect(p)
    print("SEC_13F_PREFLIGHT "+json.dumps({"source":SOURCE,"archiveUrl":URL,"bytes":size,"sha256":digest.hexdigest(),**result}))
if __name__=="__main__":main()
