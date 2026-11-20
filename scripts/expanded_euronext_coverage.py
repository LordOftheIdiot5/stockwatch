"""Validate direct Euronext report coverage using exact new identity candidates."""
import json
from collections import Counter
from euronext_price_coverage import targets,parse,MARKETS,ROOT
from delayed_exchange import eur_url,downloaded,HTTPError
from listing_identity_batch import run
from exchange_identity import valid_isin

def joined(queue,candidates):
    groups,total=targets(queue)
    records={r["id"]:r for r in queue["queues"]["euronext"]["records"]}
    ids={id_ for g in groups.values() for v in g.values() for id_ in v}
    pairs={k for g in groups.values() for k in g}
    added=0
    for c in candidates:
        id_=c["listingId"];r=records.get(id_)
        pair=(c["isin"],c["mic"])
        if not r or id_ in ids or pair in pairs or not valid_isin(c["isin"]) or r.get("mic")!=c["mic"] or r.get("figi")!=c["figi"] or r.get("isin") or c["mic"] not in MARKETS or c.get("status")!="exact_candidate_join" or c.get("reviewRequired") is not True or c.get("pricePublicationAllowed") is not False:
            raise ValueError("conflicting candidate or incorrect queue identity")
        groups[MARKETS[c["mic"]]][pair]=[id_]
        ids.add(id_);pairs.add(pair);added+=1
    return groups,total,added

def inspect(queue,candidates,fetch=downloaded):
    groups,total,added=joined(queue,candidates)
    results=[]
    for market,expected in sorted(groups.items()):
        try:
            a=parse(fetch(eur_url(market,"PREVIOUS_TRADING_DAY")),expected)
            # Do not export candidate listing-to-ISIN mappings or raw trade data.
            results.append({"market":market,"eligible":a["eligibleListings"],"matched":a["matchedListings"],"tradingDates":a["matchedTradingDates"],"counts":a["counts"],"status":"observed"})
        except HTTPError as e:
            results.append({"market":market,"status":"http_error","httpStatus":e.code,"eligible":sum(map(len,expected.values()))})
            if e.code in (401,403,429):break
        except Exception as e:
            results.append({"market":market,"status":"unavailable","errorType":type(e).__name__,"eligible":sum(map(len,expected.values()))})
    out={"pendingListings":total,"newIdentityCandidates":added,"eligible":sum(sum(map(len,g.values())) for g in groups.values()),"matched":sum(r.get("matched",0) for r in results),"markets":results,"officialCloseEstablished":False,"pricesPublished":0,"rawRowsRetained":0}
    print("EXPANDED_EURONEXT "+json.dumps(out,sort_keys=True),flush=True)
    if not out["matched"]:raise ValueError("no matched trade observations")
    return out
if __name__=="__main__":
    queue=json.loads((ROOT/"data/price-source-queue-v1.json").read_text())
    run("euronext",inspect_candidates=lambda rows:inspect(queue,rows))
