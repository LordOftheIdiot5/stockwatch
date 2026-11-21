"""V97b: aggregate exchange-local daily-bar evidence, never price observations.

Yahoo chart timestamps are NOT an official venue session calendar, and even a
target-date bar is not guaranteed to be a completed/redistributable close.
This read-only diagnostic does not modify price selection or notification gates.
"""
from collections import Counter
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

_KEYS = (
    "chartUnavailable", "barBeforeTarget", "barOnTarget",
    "barAfterTarget", "invalidTimestamp", "localDateDiffersUtc",
    "localDateBeforeTarget", "localDateOnTarget", "localDateAfterTarget",
    "unknownExchangeTimezone", "barOlderThanRetained",
    "retainedTargetDateDespiteOlderBar", "sameProviderRecovery",
)

def bar_dates(data):
    """Return exact latest available daily-bar date in UTC and venue timezone."""
    if not isinstance(data, dict):
        return None, None, "unavailable"
    bars = data.get("bars") or []
    latest = bars[-1] if bars else None
    stamp = latest.get("t") if isinstance(latest, dict) else None
    if type(stamp) not in (int, float) or not 0 < stamp < 4102444800:
        return None, None, "invalid_timestamp"
    try:
        utc = datetime.fromtimestamp(stamp, timezone.utc)
    except (ValueError, OverflowError, OSError):
        return None, None, "invalid_timestamp"
    try:
        local = utc.astimezone(ZoneInfo(data["timezone"]))
        return utc.date().isoformat(), local.date().isoformat(), "valid"
    except (KeyError, TypeError, ValueError, ZoneInfoNotFoundError):
        return utc.date().isoformat(), None, "unknown_exchange_timezone"


class SessionProbe:
    def __init__(self, target):
        self.target = target
        self.venues = {}

    def add(self, entry, data, measured, chosen, outcome):
        venue = entry.get("exchange") or (chosen or {}).get("exchange") or "Unknown"
        group = self.venues.setdefault(venue, {"tracked": 0, "counts": Counter(),
                                                "providerUtcMin": None, "providerUtcMax": None})
        group["tracked"] += 1
        c = group["counts"]
        utc_day, local_day, status = bar_dates(data)
        if status == "unavailable":
            c["chartUnavailable"] += 1
        elif status == "invalid_timestamp":
            c["invalidTimestamp"] += 1
        elif status == "unknown_exchange_timezone":
            c["unknownExchangeTimezone"] += 1
        if utc_day:
            bucket = "barBeforeTarget" if utc_day < self.target else "barAfterTarget" if utc_day > self.target else "barOnTarget"
            c[bucket] += 1
            group["providerUtcMin"] = min(group["providerUtcMin"] or utc_day, utc_day)
            group["providerUtcMax"] = max(group["providerUtcMax"] or utc_day, utc_day)
        if local_day:
            if utc_day != local_day:
                c["localDateDiffersUtc"] += 1
            bucket = "localDateBeforeTarget" if local_day < self.target else "localDateAfterTarget" if local_day > self.target else "localDateOnTarget"
            c[bucket] += 1
        saved = (chosen or {}).get("date")
        if utc_day and isinstance(saved, str) and utc_day < saved:
            c["barOlderThanRetained"] += 1
            if saved == self.target and (chosen or {}).get("priceStatus") == "retained":
                c["retainedTargetDateDespiteOlderBar"] += 1
        if (data or {}).get("recovery"):
            c["sameProviderRecovery"] += 1
        # outcome only describes the existing comparison, not an extra signal.
        if outcome == "currency_mismatch":
            c["currencyMismatch"] += 1

    def result(self):
        rows = []
        totals = Counter()
        for name, value in sorted(self.venues.items()):
            counts = {k: int(value["counts"][k]) for k in _KEYS}
            counts["currencyMismatch"] = int(value["counts"]["currencyMismatch"])
            totals.update(counts)
            rows.append({
                "name": name, "tracked": value["tracked"],
                "providerUtcEarliest": value["providerUtcMin"],
                "providerUtcLatest": value["providerUtcMax"],
                "counts": counts
            })
        return {
            "comparisonDate": self.target, "tracked": sum(r["tracked"] for r in rows),
            "counts": {k: totals[k] for k in (*_KEYS, "currencyMismatch")},
            "byExchange": rows,
            "interpretation": (
                "Provider daily-bar timestamps vs the conservative common target date. "
                "Venue-local calendar dates are informational, not proof of a completed session. "
                "Bars are not re-dated, stored as raw vendor data, or promoted to a price alert. "
                "No official venue holiday, auction cutoff, display licence or closing price is established."
            )
        }
