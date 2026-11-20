"""Aggregate condition evidence for exact missing Euronext listings; no prices."""
import json,hashlib,re
from collections import Counter,defaultdict
from euronext_price_coverage import targets,ROOT
from euronext_normalizer import rows
from delayed_exchange import downloaded,eur_url

FIELDS=("MmtMarketMechanism","MmtNegotiationIndicator","MmtModificationIndicator","MmtBenchMarkIndicator","MmtContributionToPrice","MmtAlgorithmicIndicator","MmtPublicationMode","MmtContingentTransactionIndicator","MifidPriceNotation","MissingPrice")
def inspect(raw,expected):
    it=iter(rows(raw));header=next(it)
    if not set(FIELDS)<=set(header):raise ValueError("missing reviewed condition columns")
    counts=Counter();tuples=Counter();by_field={k:Counter() for k in FIELDS};affected=defaultdict(set)
    seen=set()
    for row in it:
        key=(row["MifidInstrumentID"].strip(),row["Venue"].strip())
        counts["scanned"]+=1
        if key not in expected:continue
        counts["matched"]+=1
        flags=tuple(row[k].strip() for k in FIELDS)
        if any(not re.fullmatch(r"[A-Za-z0-9_ /.,\-]{0,40}",v) for v in flags):raise ValueError("unexpected condition token")
        tuples[flags]+=1
        if len(tuples)>500:raise ValueError("condition profile bound")
        for field,flag in zip(FIELDS,flags):by_field[field][flag]+=1
        mod=flags[2];contrib=flags[4]
        if mod in ("CANC","AMND"):
            counts["revisionReports"]+=1;affected["revision"].add(key)
        if contrib in ("NPFT","TNCP"):
            counts["nonPriceFormation"]+=1;affected["nonPriceFormation"].add(key)
        uid=row["TradeUniqueIdentifier"].strip()
        if not uid:counts["missingId"]+=1;affected["missingId"].add(key)
        elif (key,uid) in seen:counts["repeatedId"]+=1;affected["repeatedId"].add(key)
        else:seen.add((key,uid))
    return {"fields":list(FIELDS),"counts":dict(counts),"flagCounts":{k:dict(v) for k,v in by_field.items()},"profiles":[{"flags":list(k),"rows":v} for k,v in tuples.most_common()],"affectedExactPairs":{k:len(v) for k,v in affected.items()},"officialCloseEstablished":False,"pricePublished":False,"flagPolicyApproved":False}
def main():
    groups,_=targets(json.loads((ROOT/"data/price-source-queue-v1.json").read_text()))
    if not groups:raise ValueError("no eligible targets")
    for market,expected in sorted(groups.items()):
        url=eur_url(market,"PREVIOUS_TRADING_DAY");raw=downloaded(url);r=inspect(raw,expected)
        print("EURONEXT_CONDITIONS "+json.dumps({"market":market,"sourceSha256":hashlib.sha256(raw).hexdigest(),**r},sort_keys=True))
        if not r["counts"].get("matched"):raise SystemExit(1)
if __name__=="__main__":main()
