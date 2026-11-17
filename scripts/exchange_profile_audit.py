"""Audit Euronext report schema and condition-field coverage, in memory.
No quote values, instruments, raw rows or trade identifiers in output.
"""
from collections import Counter
from decimal import Decimal, InvalidOperation
import argparse,json,sys
import delayed_exchange as ex
from euronext_normalizer import rows

def inspect(raw):
    it=iter(rows(raw))
    header=next(it)
    flags=[c for c in header if any(s in c.casefold() for s in ("flag","condition","mmt","cancel","correction","amend","trade type","tradetype","transactiontype"))]
    counts={c:Counter() for c in flags}
    total=0
    quality=Counter()
    price_notations=Counter()
    modification=Counter()
    price_formation=Counter()
    required_review={'MifidPriceNotation','MissingPrice','MmtModificationIndicator','MmtContributionToPrice'}
    review_fields_present=required_review.issubset(header)
    for row in it:
        total+=1
        if review_fields_present:
            # No raw prices or trade IDs leave this audit. Only standardized field counts.
            notation=row['MifidPriceNotation'].strip()
            mod=row['MmtModificationIndicator'].strip()
            contribution=row['MmtContributionToPrice'].strip()
            price_notations[notation if notation in ('MONE','PERC','YIEL','BAPO','') else 'other']+=1
            modification[mod if mod in ('-','CANC','AMND','') else 'other']+=1
            price_formation[contribution if contribution in ('P','NPFT','TNCP','-','') else 'other']+=1
            quality['missing_price_field_populated' if row['MissingPrice'].strip() else 'missing_price_field_blank']+=1
            try:
                p=Decimal(row['MifidPrice'].strip())
                quality['positive_finite_price' if p.is_finite() and p>0 else 'invalid_price']+=1
            except (InvalidOperation,ValueError):quality['invalid_price']+=1
            try:
                q=Decimal(row['MifidQuantity'].strip())
                quality['positive_finite_quantity' if q.is_finite() and q>0 else 'invalid_quantity']+=1
            except (InvalidOperation,ValueError):quality['invalid_quantity']+=1
        for c in flags:
            value=row[c].strip()
            counts[c]["empty" if not value else "populated"]+=1
    return {"schemaFields":header,"conditionFields":flags,
            "conditionCoverage":{k:dict(v) for k,v in counts.items()},
            "reportRowCount":total,"reviewedFlagPolicy":False,
            "reviewFieldsPresent":review_fields_present,"priceNotationCounts":dict(price_notations),
            "modificationCounts":dict(modification),"priceFormationCounts":dict(price_formation),
            "numericQualityCounts":dict(quality),
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
