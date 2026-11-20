"""Separate provider payload quality from HTTP transport and last-known fallback."""
from collections import Counter
from datetime import datetime,timezone

def outcome(entry,data,measured,prior,chosen,error=False):
    if error:return "provider_or_parser_exception"
    if not data:return "no_usable_chart"
    if data.get("ticker")!=entry["ticker"]:return "provider_symbol_mismatch"
    if not measured:return "insufficient_history"
    if chosen.get("priceStatus")=="reported":return "reported"
    if prior and measured.get("date","")<prior.get("date",""):return "provider_older_session"
    if prior and data.get("currency")!=prior.get("currency"):return "currency_mismatch"
    if prior and measured.get("date")==prior.get("date") and not measured.get("volume") and prior.get("volume"):return "partial_same_session"
    return "invalid_or_unavailable_observation"

def summarize(rows,reasons,target):
    by_exchange={}
    for row in rows:
        exchange=row.get("exchange") or "unknown"
        status=reasons.get(row["ticker"],"unknown")
        bucket=by_exchange.setdefault(exchange,Counter())
        bucket[status]+=1
    retained_after_cutoff=0
    cutoff=datetime.fromisoformat(target+"T22:00:00+00:00")
    for r in rows:
        if r.get("priceStatus")!="retained" or r.get("date")!=target or not isinstance(r.get("volume"),(int,float)) or r["volume"]<=0:continue
        try:
            stamp=datetime.fromisoformat(r["priceObservedAt"].replace("Z","+00:00"))
            if stamp.tzinfo is not None and stamp.astimezone(timezone.utc)>=cutoff:retained_after_cutoff+=1
        except (TypeError,ValueError,KeyError,AttributeError):pass
    return {"comparisonDate":target,"outcomes":dict(Counter(reasons.values())),"byExchange":{k:dict(v) for k,v in sorted(by_exchange.items())},"retainedTargetDateObservedAfterCutoff":retained_after_cutoff,"notice":"Diagnostic counts only; retained observations remain excluded from fresh-price alerts. Cutoff is a conservative UTC heuristic, not exchange certification."}
