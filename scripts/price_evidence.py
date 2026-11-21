"""Aggregate monitored quote quality without inventing venue calendars or price rights.

The observation date belongs to the retained scanner row, not necessarily the
latest response from the upstream provider. Venue labels and MICs are only those
supplied by the existing watchlist/scanner; no MIC is guessed from a suffix.
"""
from collections import Counter
from datetime import date
from price_freshness import comparison_date, price_quality, number

QUALITY = ("comparable", "unconfirmed", "older", "no_volume", "unavailable")
AGE = ("targetDate", "oneDay", "twoToThreeDays", "fourToSevenDays", "eightPlusDays", "unknownOrFuture")


def age_bucket(row, target):
    if not row:
        return "unknownOrFuture"
    try:
        day = date.fromisoformat(row["date"])
        delta = (date.fromisoformat(target) - day).days
    except (KeyError, TypeError, ValueError):
        return "unknownOrFuture"
    if delta < 0:
        return "unknownOrFuture"
    if delta == 0:
        return "targetDate"
    if delta == 1:
        return "oneDay"
    if delta <= 3:
        return "twoToThreeDays"
    if delta <= 7:
        return "fourToSevenDays"
    return "eightPlusDays"


def build(snapshot, watchlist, now):
    target = comparison_date(now)
    by_ticker = {r["ticker"]: r for r in snapshot.get("companies", []) if r.get("ticker")}
    diag = (snapshot.get("priceDiagnostics") or {}).get("byExchange") or {}
    grouped = {}
    global_ages = Counter()
    mic_provided = 0
    for entry in watchlist.get("tickers", []):
        row = by_ticker.get(entry.get("ticker"))
        venue = (row or {}).get("exchange") or entry.get("exchange") or "Unknown"
        bucket = grouped.setdefault(venue, {
            "name": venue, "tracked": 0, "priced": 0,
            "reported": 0, "retained": 0, "retainedTargetDate": 0,
            "micProvided": 0, "quality": Counter(), "ageCalendarDays": Counter()
        })
        bucket["tracked"] += 1
        if (row or entry).get("mic") or entry.get("mic"):
            bucket["micProvided"] += 1
            mic_provided += 1
        status = price_quality(row, target)
        bucket["quality"][status] += 1
        if row and number(row.get("close")) and row["close"] > 0:
            bucket["priced"] += 1
            row_status = row.get("priceStatus")
            if row_status in ("reported", "retained"):
                bucket[row_status] += 1
            if row_status == "retained" and row.get("date") == target:
                bucket["retainedTargetDate"] += 1
            age = age_bucket(row, target)
            bucket["ageCalendarDays"][age] += 1
            global_ages[age] += 1
    result = []
    for venue, bucket in sorted(grouped.items()):
        provider = diag.get(venue)
        # A missing diagnostic is unknown, never a fabricated zero.
        bucket["providerOlderSession"] = (int(provider.get("provider_older_session", 0))
                                           if isinstance(provider, dict) else None)
        bucket["providerCurrencyMismatch"] = (int(provider.get("currency_mismatch", 0))
                                              if isinstance(provider, dict) else None)
        bucket["quality"] = {key: bucket["quality"][key] for key in QUALITY}
        bucket["ageCalendarDays"] = {key: bucket["ageCalendarDays"][key] for key in AGE}
        result.append(bucket)
    total = len(watchlist.get("tickers", []))
    return {
        "comparisonDate": target,
        "tracked": total,
        "priced": sum(r["priced"] for r in result),
        "micProvided": mic_provided,
        "micMissing": total - mic_provided,
        "ageCalendarDays": {key: global_ages[key] for key in AGE},
        "byExchange": result,
        "method": ("Conservative common 22:00 UTC weekday comparison date; "
                   "not a venue-specific exchange close or holiday calendar. "
                   "Calendar-day ages refer to retained quote dates, not the age of provider HTTP responses. "
                   "MICs are counted only when explicitly supplied; no implied venue certification. "
                   "Source outcomes describe the current provider response versus retained data.")
    }
