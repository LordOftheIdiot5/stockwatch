"""Measure Cboe reference coverage for missing Nordic prices without fetching quotes."""
import json
from collections import Counter,defaultdict
from listing_identity_batch import ROOT,run
from cboe_reference_probe import URL,LIMIT,inspect
from exchange_identity import valid_isin
from research_coverage import valid_figi
from urllib.request import Request,urlopen

def scope(queue,candidates):
    rows=queue["queues"]["nasdaq_nordic"]["records"]
    by_id={r["id"]:r for r in rows}
    if len(by_id)!=len(rows):raise ValueError("duplicate queue ID")
    matches=defaultdict(set);seen=set()
    for r in candidates:
        row=by_id.get(r["listingId"])
        if not row or r["listingId"] in seen or row.get("figi")!=r["figi"] or not valid_figi(r["figi"]) or row.get("mic")!=r["mic"] or r["mic"] not in ("XSTO","XCSE","XHEL") or not valid_isin(r["isin"]) or row.get("isin") or r.get("status")!="exact_candidate_join" or r.get("reviewRequired") is not True or r.get("pricePublicationAllowed") is not False:raise ValueError("inconsistent candidate")
        seen.add(r["listingId"])
        matches[r["mic"]].add((r["isin"],r["mic"]))
    if sum(map(len,matches.values()))!=len(seen):raise ValueError("ambiguous security pair")
    return matches,len(rows)
def fetch():
    with urlopen(Request(URL,headers={"User-Agent":"Nordl Stockwatch (+https://stocks.nordl.dev/)","Accept":"text/csv"}),timeout=30) as res:
        if res.geturl()!=URL:raise ValueError("unexpected reference redirect")
        raw=res.read(LIMIT+1)
    if len(raw)>LIMIT:raise ValueError("reference size limit")
    return raw
def audit(queue,candidates,download=fetch):
    groups,total=scope(queue,candidates)
    if not groups:raise ValueError("empty candidate scope")
    raw=download()
    result={}
    for mic,pairs in sorted(groups.items()):
        r=inspect(raw,pairs)
        result[mic]={"eligible":len(pairs),"matched":r["knownExactISINMICMatches"],"fileDate":r["fileDate"]}
    d={"missingNordicListings":total,"candidatePairs":sum(map(len,groups.values())),"matched":sum(r["matched"] for r in result.values()),"byMic":result,"pricesCollected":0,"publicPricesPublished":0,"rawRowsPersisted":False,"primaryCloseEstablished":False,"deliveryRightsReviewed":False}
    print("CBOE_NORDIC_COVERAGE "+json.dumps(d,sort_keys=True),flush=True)
    if not d["matched"]:raise ValueError("no exact reference matches")
    return d
if __name__=="__main__":
    queue=json.loads((ROOT/"data/price-source-queue-v1.json").read_text())
    run("nordic",inspect_candidates=lambda records:audit(queue,records))
