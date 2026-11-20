"""Extract exact-security FIRDS delta evidence with source locators and validity dates.
No current master state or cancellation reconciliation is inferred.
"""
from __future__ import annotations
import argparse,hashlib,json,re,tempfile,zipfile
from collections import Counter,defaultdict
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from defusedxml.ElementTree import iterparse
from esma_delta_preflight import NS,REPORT,ACTIONS,select
from esma_firds_preflight import discover,manifest,DOCS
from esma_equity_extract import ROOT,download,MAX_XML
from esma_identity_history import encode,save,read,RIGHTS
from exchange_identity import valid_isin
from gleif_isin_lei import valid_lei

def field(el,*names):
    return el.findtext("/".join(NS+n for n in names)) or None

def date_value(s):
    if s is not None:
        date.fromisoformat(s)
    return s

def timestamp_value(s):
    if s is not None:
        datetime.fromisoformat(s.replace("Z","+00:00"))
    return s

def extract(stream,expected):
    stack=[];counts=Counter();rows=[];reports=0;ordinal=0
    for event,el in iterparse(stream,events=("start","end"),forbid_dtd=True,forbid_entities=True,forbid_external=True):
        if event=="start":
            stack.append(el)
            if len(stack)>64:raise ValueError("excessive XML nesting")
            if el.tag==REPORT:reports+=1
            continue
        if el.tag==NS+"FinInstrm" and len(stack)>1 and stack[-2].tag==REPORT:
            ordinal+=1
            if len(el)!=1 or el[0].tag not in ACTIONS:raise ValueError("unknown delta action")
            record=el[0];action=ACTIONS[record.tag];counts[action]+=1
            # Cancellation uses a different identity layout. Fail closed if it is
            # not recognized; never silently skip a cancellation.
            isin=field(record,"FinInstrmGnlAttrbts","Id")
            mic=field(record,"TradgVnRltdAttrbts","Id")
            if action=="CancRcrd":
                if not isin or not mic:raise ValueError("cancellation schema requires validation")
            elif not isin or not mic:raise ValueError("missing delta identity")
            if (isin,mic) in expected:
                publication=date_value(field(record,"TechAttrbts","PblctnPrd","FrDt"))
                if not publication:raise ValueError("missing matched publication validity date")
                lei=field(record,"Issr");cfi=field(record,"FinInstrmGnlAttrbts","ClssfctnTp")
                currency=field(record,"FinInstrmGnlAttrbts","NtnlCcy")
                if action!="CancRcrd" and (not valid_lei(lei) or not re.fullmatch(r"E[A-Z]{5}",cfi or "") or not re.fullmatch(r"[A-Z]{3}",currency or "")):raise ValueError("invalid matched equity reference fields")
                rows.append({"sourceOrdinal":ordinal,"action":action,"isin":isin,"mic":mic,"listingIds":sorted(expected[(isin,mic)]),
                    "publicationFrom":publication,"publicationTo":date_value(field(record,"TechAttrbts","PblctnPrd","ToDt")),
                    "lei":lei,"cfi":cfi,"currency":currency,
                    "firstTradeAt":timestamp_value(field(record,"TradgVnRltdAttrbts","FrstTradDt")),
                    "terminationAt":timestamp_value(field(record,"TradgVnRltdAttrbts","TermntnDt"))})
                if len(rows)>100000:raise ValueError("matched record bound")
            stack[-2].remove(el);el.clear()
        stack.pop()
    if reports!=1:raise ValueError("missing or ambiguous delta report")
    return dict(counts),rows

def extract_archive(path,expected):
    with zipfile.ZipFile(path) as z:
        files=[i for i in z.infolist() if not i.is_dir()]
        if len(files)!=1 or not files[0].filename.lower().endswith(".xml") or not 0<files[0].file_size<=MAX_XML:raise ValueError("invalid delta archive")
        with z.open(files[0]) as f:return extract(f,expected)

def collect(group,expected):
    if not group["complete"] or not 1<=len(group["files"])<=16 or len(group["files"])!=group["expectedParts"]:raise ValueError("incomplete or unbounded delta group")
    parts=[];events=[];counts=Counter()
    with tempfile.TemporaryDirectory() as tmp:
        for f in group["files"]:
            path=Path(tmp)/"source.zip";digest=download(f,path);c,rows=extract_archive(path,expected)
            counts.update(c)
            parts.append({"name":f["name"],"sourceUrl":f["url"],"actionCounts":c,**digest})
            events.extend({**row,"sourceFile":f["name"]} for row in rows)
            path.unlink()
    return {"schemaVersion":1,"source":"ESMA FIRDS","sourceUrl":DOCS,"sourceRights":RIGHTS,"publicationFileDate":group["date"],"parts":parts,"sourceActionCounts":dict(counts),"matchedEvents":len(events),
        "scope":[{"isin":i,"mic":m,"listingIds":sorted(ids)} for (i,m),ids in sorted(expected.items())],
        "records":events,"notice":"Extracted and normalized exact ISIN/MIC delta evidence; original ESMA data freely available. No endorsement. Third-party rights and exceptions apply. Publication validity dates and trading dates are different; no current-state replay or consolidated cancellation reconciliation."}

def run(root=ROOT,now=None,groups=None,collector=collect,write=False):
    now=now or datetime.now(timezone.utc);today=now.date()
    inv=read(root/"data/listing-coverage-v1.json");expected=defaultdict(set)
    for row in inv["records"]:
        if valid_isin(row.get("isin")) and re.fullmatch(r"[A-Z0-9]{4}",row.get("mic") or "") and row.get("id"):expected[(row["isin"],row["mic"])].add(row["id"])
    if not expected:raise ValueError("no input identities")
    if groups is None:groups=manifest(discover(today-timedelta(days=13),today))
    base,days,latest=select(groups,today)
    if len(days)>8:raise ValueError("delta window exceeds bound")
    bydate={g["date"]:g for g in groups if g["type"]=="DLTINS"}
    snapshots=[];totals=Counter();matched=0
    for day in days:
        g=bydate[day.isoformat()];data=collector(g,expected)
        digest=hashlib.sha256(encode(data)).hexdigest();name=day.isoformat()+"-"+digest+".json"
        snapshots.append({"date":day.isoformat(),"path":"data/esma-delta-history/"+name,"sha256":digest,"sourceParts":len(data["parts"]),"sourceActions":sum(data["sourceActionCounts"].values()),"matchedEvents":data["matchedEvents"]})
        totals.update(data["sourceActionCounts"]);matched+=data["matchedEvents"]
        if write:
            dest=root/"data/esma-delta-history"/name
            if dest.exists() and dest.read_bytes()!=encode(data):raise ValueError("immutable evidence changed")
            if not dest.exists():save(dest,data)
    out={"schemaVersion":1,"status":"ok","baselineDate":base["date"],"throughDate":latest["date"],"checkedAt":now.isoformat(),"sourceActionCounts":dict(totals),"matchedEvents":matched,"eligiblePairs":len(expected),"days":snapshots,"currentStateEstablished":False,"replayComplete":False,"consolidatedCancellationReconciled":False}
    if write:
        idx=root/"data/esma-delta-history/index.json"
        if idx.exists() and read(idx).get("throughDate","")>out["throughDate"]:raise ValueError("delta date regression")
        save(idx,out)
    print("ESMA_DELTA_EVIDENCE "+json.dumps(out,sort_keys=True));return out

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--write",action="store_true");a=p.parse_args();run(write=a.write)
