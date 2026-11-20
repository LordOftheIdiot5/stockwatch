"""Resolve missing listing identities from one official ESMA equity baseline.

Only exact ISIN/MIC -> unique OpenFIGI listing FIGI joins. Weekly source
evidence, not current-state replay, a verified issuer merger, or quote rights.
No trade downloads, price values or source credentials in output.
"""
import argparse,hashlib,json,os,re,tempfile,zipfile
from collections import Counter,defaultdict
from pathlib import Path
from defusedxml.ElementTree import iterparse
from esma_equity_extract import NS,MAX_XML,download,ROOT
from esma_firds_preflight import probe
from exchange_identity import valid_isin,reconcile,universe
from gleif_isin_lei import valid_lei
from research_coverage import valid_figi
VENUES={"nordic":("XSTO","XCSE","XHEL"),"euronext":("XOSL","XPAR","XAMS","XBRU","XDUB","XLIS","XMIL"),"other":("XETR","XLON","XSWX")}
MAX_KEYS=4000
def eligible(queue,venue_group):
    venues=set(VENUES[venue_group]);out={}
    for q in queue["queues"].values():
        for row in q["records"]:
            if row.get("mic") not in venues or not valid_figi(row.get("figi")) or valid_isin(row.get("isin")):continue
            if row["id"] in out:raise ValueError("duplicate missing listing")
            out[row["id"]]=(row["figi"],row["mic"])
    return out
def extract(stream,mics):
    stack=[];count=0;keys=defaultdict(set)
    for event,el in iterparse(stream,events=("start","end"),forbid_dtd=True,forbid_entities=True,forbid_external=True):
        if event=="start":
            stack.append(el)
            if len(stack)>64:raise ValueError("excessive XML nesting")
            continue
        if el.tag==NS+"RefData":
            count+=1
            g=el.find(NS+"FinInstrmGnlAttrbts");v=el.find(NS+"TradgVnRltdAttrbts")
            if g is None or v is None:raise ValueError("invalid reference shape")
            mic=v.findtext(NS+"Id");isin=g.findtext(NS+"Id")
            cfi=g.findtext(NS+"ClssfctnTp") or ""
            if mic in mics and re.fullmatch(r"ES[A-Z]{4}",cfi):
                lei=el.findtext(NS+"Issr");currency=g.findtext(NS+"NtnlCcy")
                if not valid_isin(isin) or not valid_lei(lei) or not re.fullmatch(r"[A-Z]{3}",currency or ""):raise ValueError("invalid scoped reference fields")
                keys[(isin,mic)].add((lei,cfi,currency))
                if len(keys)>MAX_KEYS:raise ValueError("scoped key cap exceeded; narrow venue group")
            if len(stack)>1:stack[-2].remove(el)
            el.clear()
        stack.pop()
    if not count:raise ValueError("empty equity snapshot")
    return count,keys
def archive(path,mics):
    with zipfile.ZipFile(path) as z:
        files=[i for i in z.infolist() if not i.is_dir()]
        if len(files)!=1 or not files[0].filename.lower().endswith(".xml") or not 0<files[0].file_size<=MAX_XML:raise ValueError("unexpected ZIP")
        with z.open(files[0]) as stream:return extract(stream,mics)
def match(keys,rows,targets,key,mapper=reconcile):
    # Reject ambiguous ESMA tuples; reconcile against the full registry to
    # avoid hiding duplicate FIGIs or ISINs outside the missing-price subset.
    exact=sorted(k for k,v in keys.items() if len(v)==1)
    results,counts=mapper(exact,rows,key)
    retained=[]
    for r in results:
        if r["listingId"] not in targets:continue
        if (r["figi"],r["mic"])!=targets[r["listingId"]]:raise ValueError("candidate differs from queue")
        pair=(r["isin"],r["mic"])
        if pair not in keys or len(keys[pair])!=1:raise ValueError("missing exact source pair")
        lei,cfi,currency=next(iter(keys[pair]))
        retained.append({**r,"lei":lei,"cfi":cfi,"currency":currency})
    if len({r["listingId"] for r in retained})!=len(retained):raise ValueError("duplicate candidate")
    return retained,counts
def run(group,root=ROOT,api_key=None,retain_private=False):
    target=eligible(json.loads((root/"data/price-source-queue-v1.json").read_text()),group)
    if not target:raise ValueError("no eligible queue listings")
    key=api_key or os.getenv("STOCKWATCH_OPENFIGI_KEY","").strip()
    if not key:raise ValueError("OpenFIGI credential unavailable")
    full=probe()["latestEquityFullSet"];files=full["files"]
    if not full["complete"] or not 1<=len(files)<=8:raise ValueError("invalid baseline manifest")
    total=0;keys=defaultdict(set);parts=[]
    with tempfile.TemporaryDirectory() as tmp:
        for f in files:
            p=Path(tmp)/"equity.zip";meta=download(f,p);n,found=archive(p,set(VENUES[group]));total+=n
            for k,v in found.items():keys[k].update(v)
            if len(keys)>MAX_KEYS:raise ValueError("combined key cap exceeded; narrow venue group")
            parts.append({"name":f["name"],"sha256":meta["sha256"],"rows":n});p.unlink()
    candidates,counts=match(keys,universe(root),target,key)
    summary={"group":group,"sourceDate":full["date"],"sourceRows":total,"sourceParts":parts,"eligibleListings":len(target),"scopedSecurityPairs":len(keys),"ambiguousPairs":sum(len(v)>1 for v in keys.values()),"candidateMatches":len(candidates),"byMic":dict(Counter(r["mic"] for r in candidates)),"mappingOutcomes":counts,"currentStateEstablished":False,"publishedPrices":0,"retainedCandidateRecords":0}
    if not candidates:raise ValueError("no exact candidate matches")
    if retain_private:
        from listing_identity_r2 import archive_live
        summary.update(archive_live(summary,candidates,target))
    print("LISTING_IDENTITY_BATCH "+json.dumps(summary,sort_keys=True),flush=True)
    return summary
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--group",choices=VENUES,default="nordic");p.add_argument("--retain-private",action="store_true");a=p.parse_args()
    try:run(a.group,retain_private=a.retain_private)
    except Exception as e:
        # Avoid propagating URLs or payloads from upstream exceptions.
        print("LISTING_IDENTITY_FAILED "+type(e).__name__,flush=True)
        raise SystemExit(1) from None
