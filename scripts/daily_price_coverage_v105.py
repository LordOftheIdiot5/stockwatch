"""V105: source-dated daily coverage and missing-price recovery audit for all listing IDs.

Reads existing published scanner / inventory metadata only. Never fetches quotes,
claims exchange-close certification, copies vendor bars, overwrites the scanner,
or assumes that a dated A/B pair observation is a daily market quote.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone, date
from pathlib import Path

from price_freshness import comparison_date, price_quality

ROOT = Path(__file__).resolve().parents[1]


def date_value(value):
    if not isinstance(value, str):
        return None
    try:
        d = date.fromisoformat(value)
    except ValueError:
        return None
    return d.isoformat() if d.isoformat() == value else None


def build(coverage, signals, health, entitlements):
    if (not isinstance(coverage, dict) or coverage.get("schemaVersion") != 1
            or not isinstance(coverage.get("records"), list)
            or not isinstance(signals, dict) or not isinstance(signals.get("companies"), list)
            or not isinstance(health, dict) or not isinstance(entitlements, dict)):
        raise ValueError("Missing required original Stockwatch inputs")
    records = coverage["records"]
    if not 1 <= len(records) <= 5000:
        raise ValueError("Invalid full listing denominator")
    if len({r.get("id") for r in records}) != len(records):
        raise ValueError("Duplicate listing IDs")
    summary = coverage.get("summary") or {}
    if summary.get("listings") != len(records):
        raise ValueError("Published directory total does not match listing rows")

    scan_timestamp = datetime.fromisoformat(signals["generated"].replace("Z", "+00:00"))
    if scan_timestamp.tzinfo is None:
        raise ValueError("Scanner time must have timezone")
    if signals["generated"] != coverage.get("generated"):
        raise ValueError("Directory snapshot must use exact same scan generation")
    target = comparison_date(scan_timestamp)
    price_health = health.get("priceFreshness") or {}
    if price_health.get("comparisonDate") != target:
        raise ValueError("Source quality day differs from directory scan day")

    quote_by_id = {r["ticker"]: r for r in signals["companies"] if r.get("ticker")}
    if len(quote_by_id) != len(signals["companies"]):
        raise ValueError("Duplicate monitored quote IDs")
    monitor_ids = {r["id"] for r in records if r.get("group") == "monitored"}
    if monitor_ids != set(quote_by_id):
        raise ValueError("Monitored directory and scanner identity mismatch")

    counts = Counter()
    by_venue = defaultdict(Counter)
    queue = []
    valid_groups = {"monitored", "target", "registry"}
    valid_source_statuses = {"scanner", "pair_observation", "missing"}
    for listing in records:
        ident = listing["id"]
        group = listing.get("group")
        venue = listing.get("venue")
        if group not in valid_groups or not isinstance(venue, str) or not venue:
            raise ValueError("Unknown listing group or venue")
        status = listing.get("priceStatus")
        if status not in valid_source_statuses:
            raise ValueError("Unknown price observation classification")
        d = date_value(listing.get("priceDate"))
        if (status == "missing") != (d is None):
            raise ValueError("Missing/date coverage contradiction")
        if d and d > scan_timestamp.date().isoformat():
            raise ValueError("Future price date in research inventory")
        exact = listing.get("identityStatus") == "isin_and_mic" and bool(listing.get("isin")) and bool(listing.get("mic"))
        history = listing.get("licensedHistory") is True
        c = by_venue[venue]
        for slot in (counts, c):
            slot["listings"] += 1
            slot[group] += 1
            if status == "missing":
                slot["missingPrice"] += 1
            else:
                slot["datedPrice"] += 1
            if status == "pair_observation":
                slot["pairOnly"] += 1
            if d == target:
                slot["targetDatedPrice"] += 1
            if d is not None and d < target:
                slot["olderDatedPrice"] += 1
            if exact:
                slot["exactIdentity"] += 1
            else:
                slot["identityNeedsReview"] += 1
            if history:
                slot["licensedHistory"] += 1
            else:
                slot["historyMissing"] += 1
        quality = None
        if group == "monitored":
            quality = price_quality(quote_by_id[ident], target)
            c["monitored"+quality.capitalize()] += 1
            counts["monitored"+quality.capitalize()] += 1
        reasons = []
        if status == "missing":
            reasons.append("no_saved_price")
        elif d < target:
            reasons.append("older_than_comparison_date")
        if status == "pair_observation":
            reasons.append("pair_reference_not_daily_series")
        if quality in ("unconfirmed", "no_volume", "unavailable"):
            reasons.append("monitored_source_quality_"+quality)
        if not exact:
            reasons.append("exact_isin_mic_review_required")
        if not history:
            reasons.append("licensed_history_not_connected")
        if reasons:
            queue.append({
                "id": ident, "name": listing.get("name") or ident,
                "venue": venue, "group": group, "lastSavedDate": d,
                "lastSavedKind": status, "quality": quality,
                "reviewedIdentity": exact, "licensedHistory": history,
                "needsSourcePrice": status == "missing",
                "needsDailyVerification": not (group == "monitored" and quality == "comparable"),
                "reasons": reasons
            })
    if counts["datedPrice"] != summary.get("priced") or counts["missingPrice"] != summary.get("missingPrice"):
        raise ValueError("Price counts disagree with published listing inventory")
    if counts["listings"] != counts["datedPrice"] + counts["missingPrice"]:
        raise ValueError("Incomplete price status partition")

    expected_quality = price_health.get("equities") or {}
    for key in ("comparable", "older", "unconfirmed", "no_volume", "unavailable"):
        if counts["monitored"+key.capitalize()] != expected_quality.get(key):
            raise ValueError("Per-company source status disagrees with published daily source health: "+key)

    policies = entitlements.get("sources") or []
    if not isinstance(policies, list):
        raise ValueError("Invalid source permission registry")
    approved = 0
    for item in policies:
        flags = item.get("permissions") or {}
        if all(flags.get(key) is True for key in ("productionCollection", "privateRetention", "publicDisplay")):
            approved += 1

    scorecard = {
        "schemaVersion": 1,
        "generated": signals["generated"],
        "comparisonDate": target,
        "target": "One verified price per listing per local exchange trading session, preserving more frequent feeds",
        "comparisonMethod": "Conservative UTC weekday cutoff; exchange-specific holiday/session and true official EOD certification require separate evidence",
        "summary": {
            "listings": counts["listings"],
            "datedPrice": counts["datedPrice"],
            "missingPrice": counts["missingPrice"],
            "targetDatedPrice": counts["targetDatedPrice"],
            "olderDatedPrice": counts["olderDatedPrice"],
            "monitored": counts["monitored"],
            "monitoredComparableHeuristic": counts["monitoredComparable"],
            "monitoredOlder": counts["monitoredOlder"],
            "monitoredNo_volume": counts["monitoredNo_volume"],
            "monitoredUnconfirmed": counts["monitoredUnconfirmed"],
            "monitoredUnavailable": counts["monitoredUnavailable"],
            "pairOnly": counts["pairOnly"],
            "exactIdentity": counts["exactIdentity"],
            "identityNeedsReview": counts["identityNeedsReview"],
            "licensedHistory": counts["licensedHistory"],
            "historyMissing": counts["historyMissing"],
            "rightsClearedCandidateProducts": approved,
            "exchangeCertifiedDailyQuotes": None
        },
        "byVenue": [
            {"venue": venue, **{key: values.get(key, 0) for key in (
                "listings", "monitored", "target", "registry", "datedPrice",
                "targetDatedPrice", "olderDatedPrice", "missingPrice", "pairOnly",
                "monitoredComparable", "monitoredOlder", "monitoredNo_volume",
                "monitoredUnconfirmed", "monitoredUnavailable",
                "exactIdentity", "identityNeedsReview", "licensedHistory", "historyMissing"
            )}}
            for venue, values in sorted(by_venue.items(), key=lambda x: (-x[1]["missingPrice"], x[0]))
        ],
        "notice": "A dated price is not proof of an exchange-certified daily close or rights to archive/re-distribute quotes. A/B pair references are not full historical series. Counts here do not alter the existing heatmap, fast price scanner, prices or charts."
    }
    queue.sort(key=lambda r: (
        0 if r["needsSourcePrice"] else 1 if r["needsDailyVerification"] else 2,
        0 if r["reviewedIdentity"] else 1,
        r["venue"], r["id"]
    ))
    recovery = {
        "schemaVersion": 1, "generated": signals["generated"],
        "comparisonDate": target, "totalListings": len(records),
        "candidates": queue,
        "unpricedQueue": sum(x["needsSourcePrice"] for x in queue),
        "notice": "Metadata-only operator work queue. No automated vendor queries, no quote source credentials, and no permission to collect or publish market data."
    }
    return scorecard, recovery


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=ROOT / "data/daily-price-coverage-v105.json")
    parser.add_argument("--queue", type=Path, default=ROOT / "data/daily-price-recovery-v105.json")
    args = parser.parse_args()
    def read(path):
        return json.loads((ROOT / path).read_text(encoding="utf-8"))
    summary, queue = build(
        read("data/listing-coverage-v1.json"),
        read("data/signals.json"),
        read("data/source-health.json"),
        read("scripts/source_entitlements_v102.json")
    )
    for path, obj in ((args.out, summary), (args.queue, queue)):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(obj, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
        temp.replace(path)
    print("V105_DAILY_COVERAGE "+json.dumps({
        "asOf": summary["comparisonDate"],
        "listings": summary["summary"]["listings"],
        "targetDatedPrice": summary["summary"]["targetDatedPrice"],
        "monitoredComparableHeuristic": summary["summary"]["monitoredComparableHeuristic"],
        "missingPrice": summary["summary"]["missingPrice"],
        "queue": len(queue["candidates"]),
        "exchangeCertified": summary["summary"]["exchangeCertifiedDailyQuotes"]
    }, sort_keys=True))


if __name__ == "__main__":
    main()
