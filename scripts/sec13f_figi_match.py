"""Read-only exact-FIGI SEC 13F candidate join. No ownership publication."""
import argparse,hashlib,json,os,tempfile,zipfile
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal,InvalidOperation
from pathlib import Path
from urllib.request import Request,urlopen
from sec13f_source import URL,SOURCE,rows,unit
from us_figi_bridge import probe,ROOT

def index_candidates(bridge):
    ids=defaultdict(set)
    for r in bridge["records"]:
        if r["status"]!="candidate" or len(r["candidates"])!=1:continue
        for level,value in r["candidates"][0].items():
            ids[value].add((r["listingId"],level))
    return ids

def nonnegative(s):
    try:d=Decimal(s)
    except (InvalidOperation,TypeError,ValueError):raise ValueError("invalid amount")
    if not d.is_finite() or d<0:raise ValueError("invalid amount")
    return d

def match(path,bridge,evidence=None):
    known=index_candidates(bridge)
    submissions={};covers={};stats=Counter();by_listing=defaultdict(Counter);keys=set();periods=Counter()
    with zipfile.ZipFile(path) as z:
        if len(z.infolist())>30 or sum(f.file_size for f in z.infolist())>3*1024**3:raise ValueError("archive bound")
        for row in rows(z,"SUBMISSION"):
            a=row["ACCESSION_NUMBER"]
            if a in submissions:raise ValueError("duplicate submission")
            filed=datetime.strptime(row["FILING_DATE"],"%d-%b-%Y").date()
            period=datetime.strptime(row["PERIODOFREPORT"],"%d-%b-%Y").date()
            if period>filed:raise ValueError("report date after filing")
            submissions[a]=(filed,period,row["SUBMISSIONTYPE"],row["CIK"])
            if len(submissions)>100000:raise ValueError("submission bound")
        for row in rows(z,"COVERPAGE"):
            a=row["ACCESSION_NUMBER"]
            if a not in submissions or a in covers:raise ValueError("cover join")
            covers[a]=row["AMENDMENTTYPE"]
        for row in rows(z,"INFOTABLE"):
            stats["sourceRows"]+=1
            if stats["sourceRows"]>10000000:raise ValueError("row bound")
            figi=row["FIGI"].strip()
            if not figi:continue
            stats["rowsWithFIGI"]+=1
            links=known.get(figi,set())
            if not links:continue
            listings={x[0] for x in links}
            if len(listings)!=1:
                stats["ambiguousFIGIRows"]+=1;continue
            a=row["ACCESSION_NUMBER"];k=(a,row["INFOTABLE_SK"])
            if not k[1] or k in keys:raise ValueError("duplicate or missing matched holding key")
            keys.add(k)
            if a not in covers or a not in submissions:raise ValueError("holding join")
            filed,period,form,manager=submissions[a]
            if form not in ("13F-HR","13F-HR/A"):raise ValueError("non-holdings filing")
            value=nonnegative(row["VALUE"]);quantity=nonnegative(row["SSHPRNAMT"])
            listing=next(iter(listings));s=by_listing[listing]
            s["matchedRows"]+=1
            stats["matchedRows"]+=1
            option=row["PUTCALL"].strip().upper();typ=row["SSHPRNAMTTYPE"].strip().upper()
            label="optionRows" if option in ("PUT","CALL") else "shareRowsWithoutOption" if typ=="SH" and not option else "principalRows" if typ=="PRN" and not option else "otherRows"
            s[label]+=1;stats[label]+=1
            if form.endswith("/A"):s["amendmentRows"]+=1;stats["amendmentRows"]+=1
            if row["OTHERMANAGER"].strip():s["otherManagerRows"]+=1;stats["otherManagerRows"]+=1
            for level in {x[1] for x in links}:stats["level:"+level]+=1
            periods[period.isoformat()]+=1
            if evidence is not None:
                evidence({"listingId":listing,"accession":a,"sourceRowKey":k[1],"managerCIK":manager,
                    "filingDate":filed.isoformat(),"reportPeriod":period.isoformat(),"form":form,
                    "amendmentType":covers[a],"sourceFIGI":figi,"matchLevels":sorted({x[1] for x in links}),
                    "reportedValue":str(value),"valueUnit":unit(filed),"reportedQuantity":str(quantity),
                    "quantityType":typ,"putCall":option,"otherManagerReferencePresent":bool(row["OTHERMANAGER"].strip()),
                    "classification":label,"historicalIdentityVerified":False})
    if not stats["sourceRows"]:raise ValueError("empty holdings archive")
    return {"source":SOURCE,"counts":dict(stats),"matchedListings":len(by_listing),"candidateListings":sum(r["status"]=="candidate" for r in bridge["records"]),"reportPeriods":dict(periods),"listingCounts":{k:dict(v) for k,v in sorted(by_listing.items())},"verifiedHoldings":0,"notice":"Candidate exact FIGI joins only. FIGI-level counts can overlap. Today's mapping is not proven for historical reporting dates. No ownership sum, manager ranking, position amounts or capital-flow inference."}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retain-private",action="store_true")
    args=parser.parse_args()
    bridge=probe()
    mapped_at=datetime.now(timezone.utc).isoformat(timespec="seconds")
    retained=[]
    def retain(row):
        if len(retained)>=100000:raise ValueError("candidate evidence bound")
        retained.append(row)
    agent=os.environ.get("STOCKWATCH_SEC_USER_AGENT","")
    if "@" not in agent:raise ValueError("SEC contact missing")
    size=0;digest=hashlib.sha256()
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"source.zip"
        with urlopen(Request(URL,headers={"User-Agent":agent,"Accept":"*/*"}),timeout=90) as r,p.open("wb") as f:
            if r.geturl()!=URL:raise ValueError("redirect")
            while chunk:=r.read(1024*1024):
                size+=len(chunk)
                if size>200*1024*1024:raise ValueError("compressed bound")
                digest.update(chunk);f.write(chunk)
        out=match(p,bridge,retain if args.retain_private else None)
    print("SEC_13F_FIGI_MATCH "+json.dumps({**out,"archiveUrl":URL,"sha256":digest.hexdigest(),"bytes":size},sort_keys=True))
    if args.retain_private:
        from sec13f_candidate_r2 import archive_live
        archive_live(retained,out,{"url":URL,"sha256":digest.hexdigest(),"bytes":size},mapped_at)
if __name__=="__main__":main()
