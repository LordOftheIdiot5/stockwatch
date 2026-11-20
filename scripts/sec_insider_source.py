"""Bounded SEC Forms 3/4/5 source validation, exact issuer CIK cohort."""
import csv,hashlib,io,json,os,re,tempfile,zipfile
from pathlib import Path
from collections import Counter
from datetime import datetime
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
SOURCE="https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets"
URL="https://www.sec.gov/files/datastandardsinnovation/data/insider-transactions-data-sets/2026q3_form345.zip"
DOCS="https://www.sec.gov/files/insider_transactions_readme.pdf"
REQUIRED={"SUBMISSION":"ACCESSION_NUMBER DOCUMENT_TYPE ISSUERCIK","NONDERIV_TRANS":"ACCESSION_NUMBER NONDERIV_TRANS_SK SECURITY_TITLE TRANS_DATE TRANS_CODE TRANS_ACQUIRED_DISP_CD TRANS_SHARES TRANS_PRICEPERSHARE","DERIV_TRANS":"ACCESSION_NUMBER DERIV_TRANS_SK TRANS_DATE TRANS_CODE TRANS_ACQUIRED_DISP_CD"}
def rows(z,table):
    files=[i for i in z.infolist() if i.filename.upper()==table+".TSV"]
    if len(files)!=1:raise ValueError("missing or duplicate "+table)
    with z.open(files[0]) as b,io.TextIOWrapper(b,encoding="utf-8-sig",newline="") as f:
        rd=csv.DictReader(f,delimiter=chr(9),quoting=csv.QUOTE_NONE)
        fields=rd.fieldnames or []
        if len(fields)!=len(set(fields)) or not set(REQUIRED[table].split())<=set(fields):raise ValueError("unexpected header "+table)
        for r in rd:
            if None in r or None in r.values():raise ValueError("malformed "+table)
            yield r
def inspect(path,targets):
    filings={};forms=Counter();counts=Counter();codes=Counter();matched=Counter();keys=set()
    with zipfile.ZipFile(path) as z:
        if len(z.infolist())>30 or sum(i.file_size for i in z.infolist())>512*1024**2:raise ValueError("archive bound")
        for r in rows(z,"SUBMISSION"):
            a=r["ACCESSION_NUMBER"];form=r["DOCUMENT_TYPE"];cik=r["ISSUERCIK"].zfill(10)
            if not re.fullmatch("[0-9]{10}-[0-9]{2}-[0-9]{6}",a) or a in filings or form not in {"3","3/A","4","4/A","5","5/A"} or not re.fullmatch("[0-9]{10}",cik):raise ValueError("invalid filing identity")
            filings[a]=(cik,form);forms[form]+=1
            if len(filings)>200000:raise ValueError("filing bound")
        for table in ("NONDERIV_TRANS","DERIV_TRANS"):
            for r in rows(z,table):
                counts[table]+=1
                if counts[table]>1000000:raise ValueError("transaction bound")
                a=r["ACCESSION_NUMBER"];key=(table,a,r[table+"_SK"])
                if a not in filings or not key[2] or key in keys:raise ValueError("orphan or duplicate transaction")
                keys.add(key)
                cik,form=filings[a]
                if cik not in targets:continue
                matched[cik]+=1;counts["matched:"+table]+=1
                if form.endswith("/A"):counts["matchedAmendmentRows"]+=1
                code=r["TRANS_CODE"].strip().upper();direction=r["TRANS_ACQUIRED_DISP_CD"].strip().upper()
                codes[table+":"+code+":"+direction]+=1
                if table=="NONDERIV_TRANS" and form in ("4","5"):
                    if code=="P" and direction=="A":counts["matchedReportedPurchaseRows"]+=1
                    elif code=="S" and direction=="D":counts["matchedReportedSaleRows"]+=1
        if not filings or not counts["NONDERIV_TRANS"]:raise ValueError("empty data")
    return {"filings":len(filings),"forms":dict(forms),"sourceIssuerCIKs":len({x[0] for x in filings.values()}),"targetIssuers":len(targets),"matchedIssuers":len(matched),"counts":dict(counts),"matchedCodes":dict(codes),"publishedTransactions":0,"notice":"Exact issuer CIK association only; as-filed rows, no consolidated ownership or transactions. P/S codes include open-market or private purchases/sales; amendments, other transaction types and derivatives are not combined. No reporting-owner addresses or contact data read or published."}
def main():
    agent=os.environ.get("STOCKWATCH_SEC_USER_AGENT","")
    if "@" not in agent:raise ValueError("SEC contact missing")
    seeds=json.loads((ROOT/"data/us-equity-seed.json").read_text())["records"];targets={r["cik"] for r in seeds}
    if not 1<=len(targets)<=50:raise ValueError("cohort bound")
    size=0;digest=hashlib.sha256()
    with tempfile.TemporaryDirectory() as tmp:
        p=Path(tmp)/"source.zip"
        with urlopen(Request(URL,headers={"User-Agent":agent,"Accept":"*/*"}),timeout=60) as r,p.open("wb") as f:
            if r.geturl()!=URL:raise ValueError("unexpected redirect")
            while chunk:=r.read(1024*1024):
                size+=len(chunk)
                if size>64*1024**2:raise ValueError("archive bound")
                digest.update(chunk);f.write(chunk)
        result=inspect(p,targets)
    print("SEC_INSIDER_PREFLIGHT "+json.dumps({"source":SOURCE,"documentation":DOCS,"archiveUrl":URL,"bytes":size,"sha256":digest.hexdigest(),**result},sort_keys=True))
if __name__=="__main__":main()
