"""Read-only FIRDS weekly equity snapshot extraction probe; no delta replay or publication."""
from __future__ import annotations
import hashlib,json,re,tempfile,zipfile
from collections import defaultdict
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlsplit
from defusedxml.ElementTree import iterparse
from exchange_identity import valid_isin
from gleif_isin_lei import valid_lei
from esma_firds_preflight import probe,HOSTS,NAME

ROOT=Path(__file__).resolve().parents[1]
NS="{urn:iso:std:iso:20022:tech:xsd:auth.017.001.02}"
MAX_ZIP=256*1024*1024
MAX_XML=2*1024*1024*1024

def extract(xml,expected):
    stack=[];count=0;matches=defaultdict(set)
    for event,el in iterparse(xml,events=("start","end"),forbid_dtd=True,forbid_entities=True,forbid_external=True):
        if event=="start":
            stack.append(el);continue
        if el.tag==NS+"RefData":
            count+=1
            general=el.find(NS+"FinInstrmGnlAttrbts")
            venue=el.find(NS+"TradgVnRltdAttrbts")
            if general is None or venue is None:raise ValueError("missing reference record fields")
            isin=general.findtext(NS+"Id")
            mic=venue.findtext(NS+"Id")
            if not valid_isin(isin) or not re.fullmatch(r"[A-Z0-9]{4}",mic or ""):raise ValueError("invalid security identity")
            if (isin,mic) in expected:
                lei=el.findtext(NS+"Issr")
                cfi=general.findtext(NS+"ClssfctnTp")
                currency=general.findtext(NS+"NtnlCcy")
                if not valid_lei(lei) or not re.fullmatch(r"E[A-Z]{5}",cfi or "") or not re.fullmatch(r"[A-Z]{3}",currency or ""):raise ValueError("invalid matched reference fields")
                matches[(isin,mic)].add((lei,cfi,currency))
            if len(stack)>1:stack[-2].remove(el)
            el.clear()
        stack.pop()
    if not count:raise ValueError("no recognized full-file reference records")
    return count,matches

def archive(path,expected):
    with zipfile.ZipFile(path) as z:
        xml=[i for i in z.infolist() if not i.is_dir()]
        if len(xml)!=1 or not xml[0].filename.lower().endswith(".xml") or not 0<xml[0].file_size<=MAX_XML:raise ValueError("unexpected XML archive")
        with z.open(xml[0]) as stream:
            return extract(stream,expected)

def download(file,path):
    url=file["url"];u=urlsplit(url)
    if u.scheme!="https" or u.hostname not in HOSTS or u.port or u.username or u.password or u.query or u.fragment or u.path.rsplit("/",1)[-1]!=file["name"] or not NAME.fullmatch(file["name"]):raise ValueError("unexpected download URL")
    h=hashlib.sha256();size=0
    with urlopen(Request(url,headers={"User-Agent":"Nordl Stockwatch (+https://stocks.nordl.dev/)","Accept":"*/*"}),timeout=60) as r,path.open("wb") as out:
        if r.geturl()!=url:raise ValueError("unexpected download redirect")
        while chunk:=r.read(1024*1024):
            size+=len(chunk)
            if size>MAX_ZIP:raise ValueError("compressed size exceeds limit")
            h.update(chunk);out.write(chunk)
    return {"bytes":size,"sha256":h.hexdigest()}

def run(root=ROOT):
    inv=json.loads((root/"data/listing-coverage-v1.json").read_text())
    expected={(r["isin"],r["mic"]) for r in inv["records"] if valid_isin(r.get("isin")) and re.fullmatch(r"[A-Z0-9]{4}",r.get("mic") or "")}
    if not expected:raise ValueError("no eligible input identities")
    full=probe()["latestEquityFullSet"];files=full["files"]
    if not full["complete"] or not 1<=len(files)<=8:raise ValueError("incomplete or unbounded equity baseline")
    total=0;combined=defaultdict(set);parts=[]
    with tempfile.TemporaryDirectory() as temp:
        for file in files:
            path=Path(temp)/"source.zip"
            checksum=download(file,path);count,matches=archive(path,expected)
            total+=count
            for key,rows in matches.items():combined[key].update(rows)
            parts.append({"name":file["name"],"sourceUrl":file["url"],"rows":count,**checksum})
            path.unlink()
    result={"snapshotDate":full["date"],"parts":parts,"sourceRows":total,"eligiblePairs":len(expected),"matchedPairs":len(combined),"ambiguousPairs":sum(len(v)>1 for v in combined.values()),"unmatchedPairs":len(expected-set(combined)),"currentStateEstablished":False,"instrumentRecordsPublished":0,"notice":"Weekly baseline only; no delta or cancellation replay. Exact ISIN/MIC; matched tuples are not persisted or published."}
    print("ESMA_EQUITY_EXTRACTION "+json.dumps(result,sort_keys=True));return result

if __name__=="__main__":run()
