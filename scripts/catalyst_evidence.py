"""Point-in-time catalyst evidence index from retained metadata and reviewed disclosures.
No new source collection, inferred amounts, cash flows or price-impact estimates.
"""
from __future__ import annotations
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from driver_attention import stamp, secure
from relationship_discovery import archived_items, validate

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = {"Earnings / results": "earnings", "Dividends": "dividend", "M&A": "acquisition",
              "Guidance": "guidance", "Contracts": "contract", "Capital & ownership": "capital",
              "Management": "management"}
RELATION_TYPES = {"supply_contract": "contract", "service_contract": "contract",
                  "equity_investment": "investment", "financing": "financing",
                  "debt_repayment": "financing", "acquisition": "acquisition",
                  "partnership": "partnership", "asset_transfer": "asset_transfer",
                  "arrangement": "arrangement"}
PERIODIC = {"10-K", "10-Q", "20-F", "40-F"}

def build(items, watchlist, us_seed, graph, now):
    if now.tzinfo is None:
        raise ValueError("Timezone required")
    known = {r["ticker"] for r in watchlist if r.get("ticker")}
    sec = {}
    for r in us_seed:
        if r.get("identityStatus") == "sec_ticker_exchange_association" and r.get("symbol") and r.get("cik") and r.get("id"):
            key = (r["symbol"], r["cik"])
            sec.setdefault(key, set()).add(r["id"])
    rows = {}
    scanned = 0
    for item in items:
        scanned += 1
        if not isinstance(item, dict) or item.get("duplicateOf") or item.get("relevance") not in ("strong", "mentioned"):
            continue
        published = stamp(item.get("published"))
        if not published or published > now or not item.get("id") or not secure(item.get("url")):
            continue
        ticker = item.get("ticker")
        is_sec = item.get("sourceFeed") == "sec_edgar"
        official = item.get("type") == "disclosure" and item.get("match") == "issuer_code" and item.get("relevance") == "strong"
        if is_sec:
            matches = sec.get((ticker, item.get("sourceIssuer")), set())
            if not official or len(matches) != 1:
                continue
            listing = next(iter(matches))
            identity = "sec_ticker_cik"
        elif ticker in known:
            listing = ticker
            identity = "existing_scanner_ticker"
        else:
            continue
        form = item.get("form")
        topic = CATEGORIES.get(item.get("category"))
        if is_sec and isinstance(form, str) and form.removesuffix("/A") in PERIODIC:
            topic = "periodic_filing"
        elif not topic:
            tags = {r.get("driver") for r in item.get("driverTags", []) if isinstance(r, dict)} if item.get("driverVersion") == 1 else set()
            topic = next((x for x in ("risk", "operations", "potential") if x in tags), None)
        if not topic:
            continue
        if not official and item.get("relevance") != "mentioned":
            continue
        key = "news:" + item["id"]
        row = {"id": key, "newsId": item["id"], "listingId": listing, "identityBasis": identity,
               "company": item.get("name") or ticker, "category": topic,
               "evidenceStatus": "issuer_headline" if official else "media_lead",
               "sourceUrl": item["url"], "publishedAt": published.isoformat(),
               "description": "", "amount": None, "eventDate": None, "counterparty": None,
               "actualCashFlow": None, "priceEffect": None}
        # Preserve source pointer, not another copy of publisher wording.
        rows[key] = row
    entities = validate(graph)
    for rel in graph["relationships"]:
        topic = RELATION_TYPES.get(rel["type"])
        if not topic or rel["reviewedOn"] > now.date().isoformat():
            continue
        a, b = entities[rel["from"]], entities[rel["to"]]
        key = "relationship:" + rel["id"]
        rows[key] = {"id": key, "relationshipId": rel["id"], "listingId": a.get("listingId"),
                     "counterpartyListingId": b.get("listingId"), "identityBasis": "reviewed_entity_registry",
                     "company": a["name"], "counterparty": b["name"], "category": topic,
                     "evidenceStatus": "reviewed_disclosure", "sourceUrl": rel["sourceUrl"],
                     "sourceLocator": rel["sourceLocator"], "disclosedOn": rel["disclosedOn"],
                     "reviewedOn": rel["reviewedOn"], "eventDate": rel.get("eventOn"),
                     "description": rel.get("subject", ""), "amount": rel["amount"],
                     "relationshipStatus": rel.get("status"), "actualCashFlow": False, "priceEffect": None}
    result = sorted(rows.values(), key=lambda r: (r.get("publishedAt") or r.get("disclosedOn"), r["id"]), reverse=True)
    return {"schemaVersion": 1, "generated": now.isoformat(), "archiveRecordsScanned": scanned,
            "counts": dict(Counter(r["evidenceStatus"] for r in result)),
            "notice": "Review leads are not verified events. Reviewed disclosures reuse existing relationship evidence; dates, amounts and cash flows are not inferred. No price forecasts.",
            "items": result}

def run(root=ROOT):
    def load(path):
        return json.loads((root / path).read_text(encoding="utf-8"))
    result = build(archived_items(root), load("watchlist.json")["tickers"],
                   load("data/us-equity-seed.json")["records"], load("data/company-relationships.json"),
                   datetime.now(timezone.utc))
    target = root / "data/catalyst-evidence-v1.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(target)
    print(json.dumps({"archiveRecordsScanned":result["archiveRecordsScanned"], "counts":result["counts"]}))
    return result

if __name__ == "__main__":
    run()
