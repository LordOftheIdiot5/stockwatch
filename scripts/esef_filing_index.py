"""European financial filing index validation using independently agreed issuer LEIs."""
import json,re,hashlib
from collections import Counter,defaultdict
from datetime import date
from pathlib import Path
from urllib.request import Request,urlopen
from gleif_isin_lei import valid_lei
ROOT=Path(__file__).resolve().parents[1]
URL="https://filings.xbrl.org/indexes/filings-2025.json"
SOURCE="https://filings.xbrl.org/docs/api"
TERMS="https://filings.xbrl.org/docs/about"
def targets(root):
    idx=json.loads((root/"data/esma-equity-history/index.json").read_text())
    p=idx["snapshot"]
    if not re.fullmatch(r"data/esma-equity-history/[0-9]{4}-[0-9]{2}-[0-9]{2}-[a-f0-9]{64}[.]json",p):raise ValueError("invalid snapshot pointer")
    raw=(root/p).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=idx["snapshotSha256"]:raise ValueError("snapshot checksum mismatch")
    d=json.loads(raw);out=defaultdict(set)
    for r in d["records"]:
        if r["status"]!="matched" or r["gleifComparison"]!="agree" or len(r["esmaObservations"])!=1:continue
        lei=r["esmaObservations"][0]["lei"]
        if not valid_lei(lei) or r["gleifLEIs"]!=[lei]:raise ValueError("invalid independently agreed LEI")
        out[lei].update(r["listingIds"])
    if not 1<=len(out)<=500:raise ValueError("target bound")
    return out
def inspect(d,wanted,year=2025):
    if not isinstance(d.get("data"),list) or len(d["data"])!=d.get("meta",{}).get("count") or not 1<=len(d["data"])<=30000:raise ValueError("incomplete filing index")
    entities={}
    for e in d.get("included",[]):
        if e.get("type")!="entity":continue
        if e["id"] in entities:raise ValueError("duplicate entity ID")
        entities[e["id"]]=e["attributes"]["identifier"]
    matches=defaultdict(list);countries=Counter();seen=set();orphans=0
    for f in d["data"]:
        if f["type"]!="filing" or f["id"] in seen:raise ValueError("duplicate or invalid filing")
        seen.add(f["id"])
        a=f["attributes"];period=date.fromisoformat(a["period_end"])
        if period.year!=year:raise ValueError("unexpected period year")
        countries[a["country"]]+=1
        entity=f["relationships"]["entity"]["data"]["id"];lei=entities.get(entity)
        if lei is None:orphans+=1;continue
        if lei not in wanted:continue
        # A missing JSON output or validation errors are counted separately, not discarded silently.
        has_json=isinstance(a.get("json_url"),str) and a["json_url"].startswith("/") and not a["json_url"].startswith("//")
        matches[lei].append({"country":a["country"],"period":period.isoformat(),"hasJSON":has_json,"errors":a.get("error_count")})
    if orphans:raise ValueError("unresolved filing/entity join")
    return {"source":SOURCE,"terms":TERMS,"periodEndYear":year,"indexedFilings":len(seen),"referenceCountries":dict(countries),"targetLEIs":len(wanted),"matchedLEIs":len(matches),"matchedFilings":sum(map(len,matches.values())),"matchedFilingsWithJSON":sum(x["hasJSON"] for arr in matches.values() for x in arr),"matchedFilingsWithNoReportedErrors":sum(x["errors"]==0 for arr in matches.values() for x in arr),"financialFactsPublished":0,"notice":"Exact issuer identity candidates from a dated ESMA/GLEIF agreement; repository is incomplete. Multiple filings/languages are separate observations. No financial values, copies of reports, or current-issuer claims published."}
def main():
    with urlopen(Request(URL,headers={"User-Agent":"Nordl Stockwatch (+https://stocks.nordl.dev/)","Accept":"*/*"}),timeout=60) as r:
        if r.geturl()!=URL:raise ValueError("unexpected redirect")
        raw=r.read(64*1024**2+1)
    if len(raw)>64*1024**2:raise ValueError("index bound")
    out=inspect(json.loads(raw),targets(ROOT))
    print("ESEF_FILING_PREFLIGHT "+json.dumps({**out,"indexUrl":URL,"sha256":hashlib.sha256(raw).hexdigest()},sort_keys=True))
if __name__=="__main__":main()
