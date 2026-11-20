"""Derive gated, source-dated last-trade candidates from official Euronext files.

An observed last eligible trade is NOT the exchange official close, may not be
complete, and cannot be publicly displayed or retained without source rights.
Default: only aggregate counts in CI, no quotes, identifiers or vendor rows.
"""
from __future__ import annotations
import json,hashlib,sys
from collections import Counter,defaultdict
from decimal import Decimal,InvalidOperation
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
from euronext_normalizer import rows
from euronext_condition_evidence import FIELDS
from euronext_price_coverage import MARKETS,ROOT
from expanded_euronext_coverage import joined
from delayed_exchange import downloaded,eur_url
from listing_identity_batch import run
from private_trade_bars import ZONES,ts

# EXACT condition tuples observed in 2026-11-19 Oslo source. All unknown
# combinations quarantine the entire affected instrument/session.
ELIGIBLE={
 ("1","-","-","-","-","ALGO","-","-","MONE",""),
 ("1","-","-","-","-","-","-","-","MONE",""),
}
EXCLUDED={
 ("3","-","-","RFPT","-","ALGO","-","-","MONE",""),
 ("3","-","-","RFPT","-","-","-","-","MONE",""),
 ("4","-","-","-","-","-","-","-","MONE",""),
}
def positive(value):
    try:d=Decimal(str(value))
    except (ValueError,InvalidOperation,TypeError):raise ValueError("invalid number") from None
    if not d.is_finite() or d<=0:raise ValueError("non-positive number")
    return d

def stage(raw,expected):
    """Return ephemeral in-memory dated last eligible trades for exact pairs.

    expected: {(isin,mic):[one already-reconciled listing id]}. Never serialize
    or log raw data, candidate IDs, prices, or matched currency without rights.
    """
    if any(len(ids)!=1 for ids in expected.values()):raise ValueError("ambiguous exact listing")
    it=iter(rows(raw));fields=next(it)
    if not set(FIELDS).issubset(fields):raise ValueError("mandatory condition fields missing")
    seen=defaultdict(dict);blocked=set();matched=set();stats=Counter()
    for row in it:
        pair=(row["MifidInstrumentID"].strip(),row["Venue"].strip())
        if pair not in expected:continue
        stats["sourceMatchedRows"]+=1;matched.add(pair)
        mic=pair[1]
        if mic not in ZONES:raise ValueError("unexpected MIC")
        stamp=row["TradingDateTime"].strip()
        try:
            trade=ts(stamp);published=ts(row["PublicationDateTime"].strip())
            local=trade.astimezone(ZoneInfo(ZONES[mic])).date().isoformat()
        except (ValueError,TypeError,KeyError):raise ValueError("malformed timestamp in matching trade") from None
        key=pair+(local,)
        flags=tuple(row[c].strip() for c in FIELDS)
        # Any unrecognised condition, correction, or non-price-forming report
        # invalidates that session instead of silently selecting a wrong last.
        if flags not in ELIGIBLE|EXCLUDED or published<trade:
            blocked.add(key);stats["unknownOrRevision"]+=1;continue
        uid=row["TradeUniqueIdentifier"].strip()
        try:
            price=positive(row["MifidPrice"]);quantity=positive(row["MifidQuantity"])
        except ValueError:
            blocked.add(key);stats["invalidNumeric"]+=1;continue
        currency=row["MifidCurrency"].strip()
        if not uid or len(uid)>200 or not currency.isalpha() or len(currency)!=3 or currency!=currency.upper():
            blocked.add(key);stats["invalidIdentityOrCurrency"]+=1;continue
        sig=(trade,published,str(price),str(quantity),currency,flags)
        old=seen[key].get(uid)
        if old is not None and old!=sig:
            blocked.add(key);stats["conflictingTradeIds"]+=1;continue
        seen[key][uid]=sig
    candidates=[];reasons=Counter()
    for key,observations in sorted(seen.items()):
        if key in blocked:reasons["blocked"]+=1;continue
        eligible=[(uid,s) for uid,s in observations.items() if s[-1] in ELIGIBLE]
        if not eligible:reasons["withoutCentralBookTrades"]+=1;continue
        currencies={s[4] for _,s in eligible}
        if len(currencies)!=1:reasons["mixedCurrency"]+=1;continue
        last_time=max(s[0] for _,s in eligible)
        latest=[s for _,s in eligible if s[0]==last_time]
        if len({s[2] for s in latest})!=1:reasons["ambiguousLastTrade"]+=1;continue
        # Float is never used to choose or compare the original trade price.
        candidates.append({"listingId":expected[key[:2]][0],"mic":key[1],"date":key[2],
            "currency":next(iter(currencies)),"lastTradePrice":latest[0][2],
            "lastTradeAt":last_time.isoformat(),"observedEligibleTrades":len(eligible),
            "classification":"observed_central_order_book_last_trade_not_official_close",
            "officialClose":False,"publicPublicationAllowed":False,"historicalRetentionApproved":False})
    # Include unknown-only sessions: otherwise an invalid last trade could
    # appear simply as an unmatched security rather than an actual quarantine.
    reasons["blocked"]+=len(blocked-set(seen))
    stats["matchedPairs"]=len(matched);stats["derivedSessions"]=len(candidates)
    return candidates,{"counts":dict(stats),"quarantined":dict(reasons)}

def inspect(queue,candidates,fetch=downloaded,window="PREVIOUS_TRADING_DAY"):
    groups,total,added=joined(queue,candidates)
    out=[];private_candidates=[]
    for market,expected in sorted(groups.items()):
        raw=fetch(eur_url(market,window))
        staged,stats=stage(raw,expected)
        private_candidates.extend(staged)
        out.append({"market":market,"sourceSha256":hashlib.sha256(raw).hexdigest(),
            "eligibleListings":sum(map(len,expected.values())),
            "ephemeralDatedObservations":len(staged),**stats})
    summary={"pendingListings":total,"newIdentityCandidates":added,
        "eligibleListings":sum(x["eligibleListings"] for x in out),
        "ephemeralDatedObservations":len(private_candidates),
        "markets":out,"publishedPrices":0,"officialCloses":0,
        "rawRowsRetained":0,"internalArchiveWritten":False}
    print("EURONEXT_PRICE_STAGE "+json.dumps(summary,sort_keys=True),flush=True)
    return summary

def main():
    queue=json.loads((ROOT/"data/price-source-queue-v1.json").read_text())
    run("euronext",inspect_candidates=lambda ids:inspect(queue,ids))

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print("EURONEXT_STAGE_FAILED "+type(exc).__name__,flush=True)
        raise SystemExit(1) from None
