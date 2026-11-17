"""Audit Euronext report schema and condition-field coverage, in memory.
No quote values, instruments, raw rows or trade identifiers in output.
"""
from collections import Counter
import argparse,json,sys
import delayed_exchange as ex
from euronext_normalizer import rows

def inspect(raw):
    it=iter(rows(raw))
    header=next(it)
    flags=[c for c in header if any(s in c.casefold() for s in ("flag","condition","mmt","cancel","correction","amend","trade type","tradetype","transactiontype"))]
    counts={c:Counter() for c in flags}
    total=0
    for row in it:
        total+=1
        for c in flags:
            value=row[c].strip()
            counts[c]["empty" if not value else "populated"]+=1
    return {"schemaFields":header,"conditionFields":flags,
            "conditionCoverage":{k:dict(v) for k,v in counts.items()},
            "reportRowCount":total,"reviewedFlagPolicy":False,
            "officialCloseVerified":False,"pricePublicationAllowed":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--market",choices=ex.MARKETS,default="OSL")
    a=p.parse_args()
    try:
        raw=ex.downloaded(ex.eur_url(a.market,"PREVIOUS_TRADING_DAY"))
        print("EXCHANGE_PROFILE "+json.dumps({"market":a.market,**inspect(raw)},sort_keys=True),flush=True)
    except Exception as e:
        print("EXCHANGE_PROFILE "+json.dumps({"market":a.market,"status":"unavailable","errorType":type(e).__name__}),flush=True)
        return 1
    return 0
if __name__=="__main__":sys.exit(main())
