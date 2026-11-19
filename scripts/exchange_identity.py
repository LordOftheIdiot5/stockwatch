"""Private exchange identity reconciliation. Never publish trade observations.

Match exact ISIN + MIC to a unique OpenFIGI instrument and existing listing.
A successful join is technical identity evidence, not a reviewed price grant.
"""
from __future__ import annotations
import argparse,csv,io,json,os,re,sys,zipfile
from collections import defaultdict,Counter
from pathlib import Path
from datetime import datetime,timezone
import delayed_exchange as ex
import research_coverage as fig
ROOT=Path(__file__).resolve().parents[1]
MARKET_MIC={"OSL":"XOSL","PAR":"XPAR","AMS":"XAMS","BRU":"XBRU","DUB":"XDUB","LIS":"XLIS","MIL":"XMIL"}
VENUES={"Oslo":"XOSL","Stockholm":"XSTO","Copenhagen":"XCSE","Helsinki":"XHEL","Paris":"XPAR","Amsterdam":"XAMS","Brussels":"XBRU","Dublin":"XDUB","Milan":"XMIL","Vienna":"XWBO","XETRA":"XETR","MCE":"XMAD","HKSE":"XHKG"}
MAX_IDENTITIES=5000
def valid_isin(s):
    if not isinstance(s,str) or not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]",s):return False
    digits="".join(str(ord(c)-55) if c.isalpha() else c for c in s)
    return sum((int(c)*2-9 if int(c)*2>9 else int(c)*2) if i%2 else int(c) for i,c in enumerate(reversed(digits)))%10==0
def read(root,path):return json.loads((root/path).read_text(encoding="utf-8"))
def universe(root=ROOT):
    watches=read(root,"watchlist.json")["tickers"]
    issuers={r["ticker"]:r for r in read(root,"data/issuer-identities.json")["entities"]}
    candidates=defaultdict(set)
    for x in read(root,"data/registered-source-status.json")["figiCandidates"]:
        if fig.valid_figi(x.get("figi")):candidates[x["ticker"]].add(x["figi"])
    coverage={r["id"]:r for r in read(root,"data/research-coverage.json")["records"]}
    rows=[]
    monitored_keys=set()
    targets=read(root,"data/research-targets.json")["targets"]
    for w in watches:
        fs=set(candidates[w["ticker"]]);i=issuers.get(w["ticker"],{})
        mic=VENUES.get(w["exchange"])
        isin=i.get("isin") if i.get("evidence") else None
        if w.get("mic")==mic and valid_isin(w.get("isin")):
            exact=[t for t in targets if t.get("mic")==mic and t.get("isin")==w["isin"] and t.get("symbol")+".OL"==w["ticker"] and mic=="XOSL"]
            if len(exact)==1 and (not isin or isin==w["isin"]):
                isin=w["isin"]
                c=coverage.get(exact[0]["id"],{});m=c.get("currentCandidate") or {}
                if c.get("mappingStatus")=="candidate" and c.get("mic")==mic and c.get("isin")==isin and c.get("symbol")==exact[0]["symbol"] and fig.valid_figi(m.get("figi")):fs.add(m["figi"])
                monitored_keys.add((mic,isin))
        rows.append({"id":w["ticker"],"mic":mic,"figi":next(iter(fs)) if len(fs)==1 else None,"isin":isin})
    for t in targets:
        if (t.get("mic"),t.get("isin")) in monitored_keys:continue
        c=coverage.get(t["id"],{});m=c.get("currentCandidate") or {}
        candidate=m.get("figi") if c.get("mappingStatus")=="candidate" and c.get("mic")==t["mic"] and c.get("symbol")==t["symbol"] and c.get("isin")==t.get("isin") else None
        rows.append({"id":"ref:"+t["id"],"mic":t["mic"],"figi":candidate,"isin":t.get("isin")})
    for r in read(root,"data/research-expansion.json")["records"]:
        rows.append({"id":"registry:"+r["mic"]+":"+r["figi"],"mic":r["mic"],"figi":r["figi"],"isin":None})
    if len({r["id"] for r in rows})!=len(rows):raise ValueError("Duplicate listing ID")
    return rows
def trade_keys(raw,mic):
    """Read only identifiers; exact MIC, no inferred segment aliases."""
    keys=set()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        files=[x for x in z.infolist() if not x.is_dir() and x.filename.lower().endswith(".csv")]
        if len(files)!=1 or files[0].file_size>ex.MAX_EXPANDED:raise ValueError("Unexpected archive")
        with z.open(files[0]) as b,io.TextIOWrapper(b,encoding="utf-8-sig",newline="") as f:
            fields=None
            for _ in range(4):
                line=f.readline()
                for sep in (",",";","\t"):
                    header=next(csv.reader([line],delimiter=sep))
                    if ex.REQUIRED.issubset(header):
                        fields=header;break
                if fields:break
            if not fields or len(fields)!=len(set(fields)):raise ValueError("Unknown header")
            for row in csv.DictReader(f,fieldnames=fields,delimiter=sep):
                isin=(row.get("MifidInstrumentID") or "").strip()
                venue=(row.get("Venue") or "").strip()
                if venue!=mic or not valid_isin(isin):continue
                keys.add((isin,venue))
                if len(keys)>MAX_IDENTITIES:raise ValueError("Identifier cap exceeded")
    return sorted(keys)
def reconcile(keys,rows,key,fetch=fig.request):
    by_figi=defaultdict(set);by_isin=defaultdict(set);by_id={}
    for r in rows:
        by_id[r["id"]]=r
        if fig.valid_figi(r.get("figi")):by_figi[(r["figi"],r["mic"])].add(r["id"])
        if valid_isin(r.get("isin")):by_isin[(r["isin"],r["mic"])].add(r["id"])
    matches=[];counts=Counter()
    if not key:raise ValueError("Existing OpenFIGI API key required for bulk identity audit")
    for start in range(0,len(keys),100):
        batch=keys[start:start+100]
        replies=fetch([{"idType":"ID_ISIN","idValue":i,"micCode":m,"marketSecDes":"Equity"} for i,m in batch],key)
        if len(replies)!=len(batch):raise ValueError("Incomplete mapping response")
        for (isin,mic),reply in zip(batch,replies):
            # Do not collapse ambiguous listings by composite or share class.
            found={x["figi"] for x in reply.get("data",[]) if isinstance(x,dict) and x.get("marketSector")=="Equity" and fig.valid_figi(x.get("figi"))}
            if len(found)!=1:
                counts["ambiguous_figi" if found else "unresolved_figi"]+=1;continue
            f=next(iter(found));ids=by_figi[(f,mic)];known=by_isin[(isin,mic)]
            if len(ids)!=1 or len(known)>1:
                counts["ambiguous_listing" if len(ids)>1 or len(known)>1 else "outside_or_unmapped_universe"]+=1;continue
            id=next(iter(ids))
            if (known and known!={id}) or (valid_isin(by_id[id].get("isin")) and by_id[id]["isin"]!=isin):
                counts["conflicting_identity"]+=1;continue
            matches.append({"listingId":id,"isin":isin,"mic":mic,"figi":f,"status":"exact_candidate_join","reviewRequired":True,"pricePublicationAllowed":False})
            counts["exact_candidate_join"]+=1
    # A listing with multiple observed ISINs is not safe to join.
    freq=Counter(r["listingId"] for r in matches)
    rejected=sum(freq[r["listingId"]]>1 for r in matches)
    if rejected:
        counts["exact_candidate_join"]-=rejected;counts["conflicting_identity"]+=rejected
        matches=[r for r in matches if freq[r["listingId"]]==1]
    return matches,dict(counts)
def save_private(path,result):
    path=Path(path).expanduser().resolve()
    if path==ROOT or ROOT in path.parents:raise ValueError("Private output must be outside repository")
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".tmp");temp.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8");temp.replace(path)
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--market",choices=MARKET_MIC,default="OSL")
    p.add_argument("--archive",type=Path,help="Existing authorized private Euronext ZIP")
    p.add_argument("--private-output",type=Path)
    a=p.parse_args()
    raw=a.archive.read_bytes() if a.archive else ex.downloaded(ex.eur_url(a.market,"PREVIOUS_TRADING_DAY"))
    keys=trade_keys(raw,MARKET_MIC[a.market])
    if not keys:raise ValueError("No valid exact-venue identifiers; inspect exchange segment and file privately")
    rows=universe()
    matches,counts=reconcile(keys,rows,os.getenv("STOCKWATCH_OPENFIGI_KEY","").strip())
    if a.private_output:save_private(a.private_output,{"checkedAt":datetime.now(timezone.utc).isoformat(),"market":a.market,"universe":len(rows),"counts":counts,"matches":matches})
    # Public CI emits only pass/fail metadata, no exchange identifiers or records.
    print(json.dumps({"market":a.market,"registryListings":len(rows),"mappingValidated":bool(matches),"privateOutput":bool(a.private_output),"publicPricePublication":False}))
    return 0 if matches else 1
if __name__=="__main__":sys.exit(main())
