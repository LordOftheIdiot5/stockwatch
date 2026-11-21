"""V104b presentation-layer policy: add licensed EOD charts without replacing faster feeds.

Pure composition only; existing source scanner, heatmaps and overlays are untouched.
Caller must verify original provider rights and exact issuer identity separately.
No public data is enabled or obtained by this module.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from math import isfinite


def _day(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _positive(value):
    if isinstance(value, bool):
        return False
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return number.is_finite() and number > 0


def _existing(row, listing_id):
    return (isinstance(row, dict) and row.get("ticker") == listing_id
            and row.get("referenceOnly") is not True
            and row.get("unavailable") is not True
            and _positive(row.get("close"))
            and _day(row.get("date")) is not None
            and isinstance(row.get("currency"), str)
            and len(row["currency"]) == 3
            and row["currency"].isupper())


def _licensed_history(series, listing_id, public_display_approved):
    """A validated chart_rows result AND a separate caller approval are required."""
    if (public_display_approved is not True or not isinstance(series, dict)
            or series.get("status") != "ok" or series.get("listingId") != listing_id):
        return []
    bars = series.get("bars")
    if not isinstance(bars, list) or len(bars) < 2:
        return []
    output = []
    seen = set()
    currency = mic = kind = None
    for bar in bars:
        if not isinstance(bar, dict):
            return []
        day = _day(bar.get("date"))
        if day is None or day in seen or not _positive(bar.get("close")):
            return []
        if not all(isinstance(bar.get(k), str) and bar[k] for k in ("mic", "currency", "kind", "sourceUrl", "publishedAt")):
            return []
        if not bar["sourceUrl"].startswith("https://"):
            return []
        if len(bar["currency"]) != 3 or not bar["currency"].isupper():
            return []
        if currency is None:
            currency, mic, kind = bar["currency"], bar["mic"], bar["kind"]
        if (currency, mic, kind) != (bar["currency"], bar["mic"], bar["kind"]):
            return []
        seen.add(day)
        output.append(dict(bar))
    output.sort(key=lambda x: x["date"])
    return output


def compose_display_layers(listing_id, existing_quote=None, eod_series=None, public_display_approved=False):
    """Never mutate or delete existing scanner observations or visualization inputs.

    - Existing valid quote wins on the SAME/NEWER exchange date: EOD cannot
      downgrade a more frequently updated feed.
    - A newer authorized EOD close can fill a gap without deleting the older
      existing observation; the source-dated original remains separately available.
    - EOD bars are historical chart inputs ONLY, not replacements for heatmap
      movement, intraday alerts, scanner scheduling or actual market breadth.
    - Different currencies or unknown identities are not silently mixed.
    """
    if not isinstance(listing_id, str) or not listing_id:
        raise ValueError("Exact listing ID required")
    fast = dict(existing_quote) if _existing(existing_quote, listing_id) else None
    history = _licensed_history(eod_series, listing_id, public_display_approved)
    last = history[-1] if history else None
    if fast is not None and last is not None and fast["currency"] != last["currency"]:
        history, last = [], None
    if fast is not None and (last is None or fast["date"] >= last["date"]):
        selected, layer = dict(fast), "existing_observation"
    elif last is not None:
        selected = {
            "ticker": listing_id, "close": float(last["close"]),
            "date": last["date"], "currency": last["currency"],
            "mic": last["mic"], "sourceUrl": last["sourceUrl"],
            "publishedAt": last["publishedAt"], "kind": last["kind"],
            "priceStatus": "licensed_eod", "frequency": "daily"
        }
        layer = "licensed_eod_fallback"
    else:
        selected, layer = None, "unavailable"
    return {
        "listingId": listing_id, "selectedLayer": layer, "displayQuote": selected,
        "existingObservation": fast, "licensedDailyHistory": history,
        "heatmapSignalSource": "existing_scanner_only",
        "intradayUpdatesPreserved": True,
        "note": "EOD history is additive; no synthetic ticks, current-session moves or fallback price-date changes."
    }
