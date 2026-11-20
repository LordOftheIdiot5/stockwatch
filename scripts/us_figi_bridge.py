"""US seed security mapping candidates, not verified ownership or CUSIP publication."""
import json,os,time
from collections import Counter,defaultdict
from pathlib import Path
from urllib.request import Request,urlopen
from exchange_identity import fig
ROOT=Path(__file__).resolve().parents[1]
URL="https://api.openfigi.com/v3/mapping"
def jobs(seeds):
    seen=set();out=[]
    for r in seeds:
        if r.get("identityStatus")!="sec_ticker_exchange_association" or r.get("mic") not in {"XNYS","XNAS","XASE"}:continue
        if r["id"] in seen:raise ValueError("duplicate seed")
        seen.add(r["id"])
        out.append((r,{"idType":"TICKER","idValue":r["symbol"],"micCode":r["mic"],"marketSecDes":"Equity","currency":"USD","includeUnlistedEquities":False}))
    return out
def classify(seed,result):
    if not isinstance(result,dict):raise ValueError("invalid mapping result")
    if "error" in result:
        raise ValueError("mapping API reported error")
    data=result.get("data",[])
    if not isinstance(data,list):raise ValueError("invalid result data")
    # Filter exact symbols and ordinary common stock only; ticker aliases,
    # preferred shares and other equity types are not inferred.
    valid=set()
    for r in data:
        if r.get("ticker")!=seed["symbol"] or r.get("marketSector")!="Equity" or r.get("securityType2")!="Common Stock":continue
        ids=tuple(r.get(k) for k in ("figi","compositeFIGI","shareClassFIGI"))
        if all(fig.valid_figi(x) for x in ids):valid.add(ids)
    return {"listingId":seed["id"],"cik":seed["cik"],"mic":seed["mic"],"symbol":seed["symbol"],"status":"candidate" if len(valid)==1 else "ambiguous" if valid else "unmatched","candidates":[dict(zip(("figi","compositeFIGI","shareClassFIGI"),v)) for v in sorted(valid)],"verified":False}
def request(payload,key):
    headers={"Content-Type":"application/json","Accept":"application/json","User-Agent":"Nordl Stockwatch (+https://stocks.nordl.dev/)","X-OPENFIGI-APIKEY":key}
    with urlopen(Request(URL,data=json.dumps(payload).encode(),headers=headers),timeout=30) as r:
        if r.geturl()!=URL:raise ValueError("unexpected redirect")
        raw=r.read(2000001)
    if len(raw)>2000000:raise ValueError("mapping response exceeds limit")
    return json.loads(raw)
def probe(root=ROOT,fetch=request,key=None,pause=time.sleep):
    key=key if key is not None else os.environ.get("STOCKWATCH_OPENFIGI_KEY","").strip()
    if not key:raise ValueError("OpenFIGI key missing")
    seeds=json.loads((root/"data/us-equity-seed.json").read_text())["records"];work=jobs(seeds)
    if not 1<=len(work)<=50:raise ValueError("seed scope exceeds bound")
    results=[]
    for i in range(0,len(work),10):
        batch=work[i:i+10];ans=fetch([p for s,p in batch],key)
        if not isinstance(ans,list) or len(ans)!=len(batch):raise ValueError("mapping response count mismatch")
        results.extend(classify(s,a) for (s,p),a in zip(batch,ans));pause(.3)
    owners=defaultdict(set)
    for r in results:
        if r["status"]=="candidate":
            for k,v in r["candidates"][0].items():owners[v].add(r["listingId"])
    overlaps={x for x,v in owners.items() if len(v)>1}
    for r in results:
        if r["status"]=="candidate" and any(v in overlaps for v in r["candidates"][0].values()):r["status"]="cross_listing_review"
    out={"source":URL,"scope":"US SEC ticker/exchange seeds; exact symbol ordinary common equity mapping candidates","counts":dict(Counter(r["status"] for r in results)),"eligible":len(work),"records":results,"verifiedHoldings":0}
    print("US_FIGI_BRIDGE "+json.dumps({k:v for k,v in out.items() if k!="records"}))
    return out
if __name__=="__main__":probe()
