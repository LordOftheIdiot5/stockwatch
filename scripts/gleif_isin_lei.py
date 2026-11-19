"""Bounded ANNA/GLEIF full-file import for known exact ISINs; never infer issuer identity."""
from __future__ import annotations
import csv,hashlib,io,json,re,zipfile
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from exchange_identity import valid_isin
ROOT=Path(__file__).resolve().parents[1]
SOURCE="https://www.gleif.org/en/lei-data/lei-mapping/download-isin-to-lei-relationship-files/"
BASE="https://isinmapping.gleif.org/api/v2/isin-lei/"
LIMIT=96*1024*1024
EXPANDED=768*1024*1024
def valid_lei(s):
    if not isinstance(s,str) or not re.fullmatch(r"[A-Z0-9]{18}[0-9]{2}",s):return False
    n=0
    for c in s:
        for d in (str(ord(c)-55) if c.isalpha() else c):n=(10*n+int(d))%97
    return n==1
def get(url):
    with urlopen(Request(url,headers={"User-Agent":"StockwatchResearch/1.0 (+https://stocks.nordl.dev/)","Accept":"application/zip"}),timeout=60) as response:
        if response.geturl()!=url:raise ValueError("unexpected_redirect")
        raw=response.read(LIMIT+1)
    if len(raw)>LIMIT:raise ValueError("archive_size")
    return raw
def inspect(raw,expected):
    matches=defaultdict(set);total=invalid=0
    if len(raw)>LIMIT:raise ValueError("archive_size")
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        files=[i for i in z.infolist() if not i.is_dir() and i.filename.lower().endswith(".csv")]
        if len(files)!=1 or files[0].file_size>EXPANDED:raise ValueError("unexpected_archive")
        with z.open(files[0]) as b,io.TextIOWrapper(b,encoding="utf-8-sig",newline="") as f:
            reader=csv.DictReader(f)
            cols={s.strip().upper():s for s in (reader.fieldnames or [])}
            if len(cols)!=len(reader.fieldnames or []) or not {"ISIN","LEI"}.issubset(cols):raise ValueError("unexpected_schema")
            for row in reader:
                total+=1
                if None in row or any(v is None for v in row.values()):raise ValueError("malformed_row")
                isin=row[cols["ISIN"]].strip();lei=row[cols["LEI"]].strip()
                if not valid_isin(isin) or not valid_lei(lei):
                    invalid+=1;continue
                if isin in expected:matches[isin].add(lei)
    if not total or invalid==total:raise ValueError("empty_or_invalid_source")
    records=[{"isin":i,"listingIds":sorted(ids),"leis":sorted(matches[i]),"status":"matched" if len(matches[i])==1 else "ambiguous" if matches[i] else "unmatched"} for i,ids in sorted(expected.items())]
    return {"sourceRows":total,"invalidSourceRows":invalid,"matchedISINs":sum(r["status"]=="matched" for r in records),"ambiguousISINs":sum(r["status"]=="ambiguous" for r in records),"eligibleISINs":len(expected),"records":records}
def build(root=ROOT,now=None,fetch=get,write=True):
    now=now or datetime.now(timezone.utc);day=now.date().isoformat();out=root/"data/gleif-isin-lei";idx=out/"index.json"
    prior=json.loads(idx.read_text()) if idx.exists() else {}
    if write and prior.get("lastAttempt","")[:10]==day and prior.get("status")=="ok":return prior
    inventory=json.loads((root/"data/listing-coverage-v1.json").read_text())
    expected=defaultdict(set)
    for row in inventory["records"]:
        if valid_isin(row.get("isin")) and row.get("id"):expected[row["isin"]].add(row["id"])
    if not expected:raise ValueError("no_eligible_ISINs")
    stamp=now.isoformat(timespec="seconds")
    def save(p,value):
        p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(".tmp");tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");tmp.replace(p)
    try:
        for offset in (0,1,2):
            date=(now.date()-timedelta(days=offset)).isoformat()
            url=BASE+date+"/download"
            try:raw=fetch(url);break
            except HTTPError as e:
                if e.code!=404 or offset==2:raise
        data=inspect(raw,expected)
        digest=hashlib.sha256(raw).hexdigest()
        snapshot={"schemaVersion":1,"source":"ANNA/GLEIF","sourceDate":date,"sourceUrl":url,"retrievedAt":stamp,"sha256":digest,"inventoryGenerated":inventory.get("generated"),**data,"notice":"Source mapping evidence for exact input ISINs, not a reviewed issuer merger or ownership record. Missing pairs do not prove absence of an issuer. Raw archive not retained."}
        name=date+"-"+digest[:16]+".json"
        result={"schemaVersion":1,"status":"ok","lastAttempt":stamp,"lastSuccess":stamp,"sourceDate":date,"sourceUrl":SOURCE,"snapshot":"data/gleif-isin-lei/"+name,**{k:v for k,v in data.items() if k!="records"}}
        if write:
            if not (out/name).exists():save(out/name,snapshot)
            else:
                existing=json.loads((out/name).read_text())
                if existing.get("records")!=data["records"]:
                    name=date+"-"+digest[:16]+"-"+hashlib.sha256(json.dumps(data["records"],sort_keys=True).encode()).hexdigest()[:12]+".json"
                    result["snapshot"]="data/gleif-isin-lei/"+name
                    if not (out/name).exists():save(out/name,snapshot)
            save(idx,result)
        print("GLEIF_MAPPING "+json.dumps(result,sort_keys=True));return result
    except Exception as e:
        result={**prior,"schemaVersion":1,"status":"retained_after_error" if prior.get("lastSuccess") else "unavailable","lastAttempt":stamp,"errorType":type(e).__name__,"sourceUrl":SOURCE}
        if write:save(idx,result)
        print("GLEIF_MAPPING "+json.dumps(result,sort_keys=True))
        raise
if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--probe",action="store_true");a=p.parse_args();build(write=not a.probe)
