"""Preserve immutable, dated FIRDS weekly evidence for exact known securities.
Not a live security master: no delta replay, price rights or forced issuer merges.
"""
from __future__ import annotations
import argparse,hashlib,json,re,tempfile
from collections import defaultdict,Counter
from datetime import datetime,timezone
from pathlib import Path
from esma_equity_extract import archive,download,ROOT
from esma_firds_preflight import probe,DOCS
from exchange_identity import valid_isin
from gleif_isin_lei import valid_lei

RIGHTS="https://registers.esma.europa.eu/publication/legalNoticePage"
NOTICE="Selected and normalized ESMA FIRDS reference facts. Original data is available free of charge from ESMA; ESMA does not endorse Nordl. Third-party rights and any stated exceptions remain applicable. Weekly snapshot evidence only; subsequent modifications, cancellations and terminations not applied."
def read(path):
    return json.loads(path.read_text(encoding="utf-8"))
def encode(obj):
    return (json.dumps(obj,sort_keys=True,ensure_ascii=False,indent=2)+"\n").encode()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp");tmp.write_bytes(encode(value));tmp.replace(path)

def gleif(root):
    """Return dated comparison evidence; missing/unavailable is not disagreement."""
    try:
        idx=read(root/"data/gleif-isin-lei/index.json")
        p=idx["snapshot"]
        if not re.fullmatch(r"data/gleif-isin-lei/\d{4}-\d{2}-\d{2}-[a-f0-9]{16}(?:-[a-f0-9]{12})?\.json",p):raise ValueError("invalid GLEIF pointer")
        snap=read(root/p)
        if snap["sourceDate"]!=idx["sourceDate"]:raise ValueError("GLEIF date mismatch")
        result={}
        for r in snap["records"]:
            if valid_isin(r.get("isin")) and all(valid_lei(x) for x in r["leis"]):
                result[r["isin"]]=set(r["leis"])
        return result,{"sourceDate":snap["sourceDate"],"snapshot":p,"status":idx["status"]}
    except (OSError,ValueError,KeyError,TypeError):
        return {},{"sourceDate":None,"snapshot":None,"status":"unavailable"}

def collect(manifest,expected):
    full=manifest["latestEquityFullSet"];files=full["files"]
    if not full["complete"] or not 1<=len(files)<=8 or len(files)!=full["expectedParts"]:raise ValueError("incomplete or unbounded equity baseline")
    combined=defaultdict(set);parts=[]
    with tempfile.TemporaryDirectory() as temp:
        for file in files:
            path=Path(temp)/"source.zip"
            digest=download(file,path);count,matches=archive(path,expected)
            for key,values in matches.items():combined[key].update(values)
            parts.append({"name":file["name"],"sourceUrl":file["url"],"rows":count,**digest})
            path.unlink()
    return combined,parts

def make_snapshot(manifest,expected,matches,parts,gmap,gmeta):
    full=manifest["latestEquityFullSet"]
    if not full["complete"] or len(parts)!=full["expectedParts"] or {p["name"] for p in parts}!={p["name"] for p in full["files"]}:raise ValueError("incomplete source parts")
    if not set(matches)<=set(expected):raise ValueError("unexpected identity")
    rows=[]
    for (isin,mic),ids in sorted(expected.items()):
        values=sorted(matches.get((isin,mic),set()))
        esma_leis={r[0] for r in values};gleif_leis=gmap.get(isin,set())
        state="unmatched" if not values else "matched" if len(values)==1 else "ambiguous"
        comparison="not_comparable" if not esma_leis or not gleif_leis else "agree" if esma_leis==gleif_leis and len(esma_leis)==1 else "review"
        rows.append({"isin":isin,"mic":mic,"listingIds":sorted(ids),"status":state,
                     "esmaObservations":[{"lei":a,"cfi":b,"currency":c} for a,b,c in values],
                     "gleifLEIs":sorted(gleif_leis),"gleifComparison":comparison})
    return {"schemaVersion":1,"source":"ESMA FIRDS","sourceDate":full["date"],"sourceUrl":DOCS,"sourceRights":RIGHTS,"transformation":"Exact ISIN/MIC subset, normalized fields; separate GLEIF comparison",
            "gleif":gmeta,"parts":parts,"sourceRows":sum(p["rows"] for p in parts),
            "eligiblePairs":len(expected),"matchedPairs":sum(bool(r["esmaObservations"]) for r in rows),
            "ambiguousPairs":sum(r["status"]=="ambiguous" for r in rows),"unmatchedPairs":sum(r["status"]=="unmatched" for r in rows),
            "comparisonCounts":dict(Counter(r["gleifComparison"] for r in rows)),
            "currentStateEstablished":False,"notice":NOTICE,"records":rows}

def build(root=ROOT,now=None,discover=probe,fetch=collect,write=True):
    now=now or datetime.now(timezone.utc);stamp=now.isoformat(timespec="seconds")
    out=root/"data/esma-equity-history";idx=out/"index.json"
    prior=read(idx) if idx.exists() else {}
    if write and prior.get("lastAttempt","")[:10]==now.date().isoformat() and prior.get("status")=="ok":return prior
    try:
        inv=read(root/"data/listing-coverage-v1.json");expected=defaultdict(set)
        for r in inv["records"]:
            if valid_isin(r.get("isin")) and re.fullmatch(r"[A-Z0-9]{4}",r.get("mic") or "") and r.get("id"):
                expected[(r["isin"],r["mic"])].add(r["id"])
        if not expected:raise ValueError("no eligible identities")
        m=discover();gmap,gmeta=gleif(root);matches,parts=fetch(m,expected)
        snap=make_snapshot(m,expected,matches,parts,gmap,gmeta)
        if snap["sourceDate"]>now.date().isoformat() or snap["sourceDate"]<prior.get("sourceDate",""):raise ValueError("snapshot date regression")
        # Snapshot content excludes retrieval time, so unchanged input is idempotent.
        digest=hashlib.sha256(encode(snap)).hexdigest()
        name=snap["sourceDate"]+"-"+digest+".json"
        path="data/esma-equity-history/"+name
        result={k:v for k,v in snap.items() if k not in ("records","parts","gleif")}
        result.update({"status":"ok","lastAttempt":stamp,"lastSuccess":stamp,"snapshot":path,"snapshotSha256":digest,
                       "pendingUpdateSets":m["subsequentDeltaAndCancellationSets"],"deltaReplayComplete":False})
        if write:
            if (out/name).exists():
                if (out/name).read_bytes()!=encode(snap):raise ValueError("immutable snapshot mismatch")
            else:save(out/name,snap)
            save(idx,result)
        print("ESMA_IDENTITY_HISTORY "+json.dumps(result,sort_keys=True));return result
    except Exception as e:
        result={**prior,"schemaVersion":1,"status":"retained_after_error" if prior.get("lastSuccess") else "unavailable","lastAttempt":stamp,"errorType":type(e).__name__,"currentStateEstablished":False,"sourceUrl":DOCS,"sourceRights":RIGHTS,"deltaReplayComplete":False}
        if write:save(idx,result)
        print("ESMA_IDENTITY_HISTORY "+json.dumps(result,sort_keys=True));raise
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--probe",action="store_true");a=p.parse_args();build(write=not a.probe)
