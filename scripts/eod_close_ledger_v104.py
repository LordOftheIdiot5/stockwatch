"""V104a: idempotent ONE-CLOSE-PER-SESSION ledger for authorized provider EOD input.

No network scraping, automatic credential acquisition, public history export, or
unlicensed Yahoo/reference observations. SQLite stays PRIVATE outside this repo.
The separately approved daily provider adapter will supply an exact JSONL batch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

from exchange_identity import valid_isin
from source_entitlements_v102 import load, require_permission, validate as validate_entitlements

ROOT = Path(__file__).resolve().parents[1]
MAX_BATCH = 5000
MAX_FILE_BYTES = 4 * 1024 * 1024
ALLOWED_KINDS = ("primary_official_close", "alternative_venue_eod", "licensed_eod_observation")
MICS = {"XOSL", "XSTO", "XCSE", "XHEL", "XICE", "XETR", "XPAR", "XAMS", "XBRU", "XMIL",
        "XDUB", "XLIS", "XWBO", "XMAD", "XHKG", "XTAI", "XNYS", "XNAS", "XLON", "BATE", "CHIX", "CEUX"}
PROVIDER_VENUE_MIC = {
    "Oslo": {"XOSL"}, "Stockholm": {"XSTO"}, "Copenhagen": {"XCSE"},
    "Helsinki": {"XHEL"}, "Iceland": {"XICE"}, "XETRA": {"XETR"},
    "Paris": {"XPAR"}, "Amsterdam": {"XAMS"}, "Brussels": {"XBRU"},
    "Milan": {"XMIL"}, "Dublin": {"XDUB"}, "Lisbon": {"XLIS"},
    "NASDAQ US": {"XNAS"}, "NYSE US": {"XNYS"},
    # Cboe's official execution MICs are alternatives to the primary listing MIC.
    "Cboe Europe BXE": {"BATE"}, "Cboe Europe CXE": {"CHIX"},
    "Cboe Europe DXE": {"CEUX"},
}
DML = """
CREATE TABLE IF NOT EXISTS eod_daily_close (
    listing_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    mic TEXT NOT NULL,
    isin TEXT NOT NULL,
    currency TEXT NOT NULL,
    session_date TEXT NOT NULL,
    close_decimal TEXT NOT NULL,
    volume INTEGER,
    quote_kind TEXT NOT NULL,
    original_source_url TEXT NOT NULL,
    published_utc TEXT NOT NULL,
    immutable_sha256 TEXT NOT NULL,
    first_seen_utc TEXT NOT NULL,
    PRIMARY KEY(listing_id, source_id, mic, session_date)
);
CREATE TABLE IF NOT EXISTS eod_batch_receipt (
    source_id TEXT NOT NULL, batch_sha256 TEXT NOT NULL,
    processed_utc TEXT NOT NULL, rows INTEGER NOT NULL,
    PRIMARY KEY(source_id, batch_sha256)
);
"""


def https(s):
    if not isinstance(s, str):
        return False
    u = urlsplit(s)
    return u.scheme == "https" and bool(u.hostname) and not u.username and not u.password


def private_path(p):
    p = Path(p).expanduser().resolve()
    if p == ROOT or ROOT in p.parents:
        raise ValueError("Private daily-close ledger must remain outside the public repository")
    return p


def utc_stamp(s):
    try:
        x = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        raise ValueError("Invalid provider publication timestamp") from None
    if x.tzinfo is None:
        raise ValueError("Provider publication time requires an offset")
    return x.astimezone(timezone.utc).isoformat(timespec="seconds")


def price(s):
    if isinstance(s, bool):
        raise ValueError("Invalid close")
    try:
        d = Decimal(str(s))
    except (InvalidOperation, ValueError):
        raise ValueError("Invalid close") from None
    if not d.is_finite() or d <= 0 or d > Decimal("100000000000"):
        raise ValueError("Invalid close")
    return format(d.normalize(), "f")


def reviewed_map(mapping, inventory=None):
    if not isinstance(mapping, dict) or mapping.get("schemaVersion") != 1:
        raise ValueError("Missing reviewed listing map")
    rows = mapping.get("mappings")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 5000:
        raise ValueError("Invalid mapping set")
    by_id, identities = {}, set()
    for row in rows:
        ident = (row.get("mic"), row.get("isin"))
        listing = row.get("listingId")
        if (row.get("reviewed") is not True or not isinstance(listing, str) or
            not 1 <= len(listing) <= 100 or not valid_isin(row.get("isin")) or
            row.get("mic") not in MICS or
            not re.fullmatch(r"[A-Z]{3}", str(row.get("currency"))) or
            not https(row.get("evidenceUrl"))):
            raise ValueError("Identity needs exact reviewed ISIN, MIC, currency, source")
        if listing in by_id or ident in identities:
            raise ValueError("Duplicate or ambiguous security identity")
        if inventory is not None and listing not in inventory:
            raise ValueError("Unrecognized research listing ID")
        by_id[listing] = row
        identities.add(ident)
    return by_id


def validate_bar(item, source_id, mapped, source, now):
    if not isinstance(item, dict) or item.get("sourceId") != source_id:
        raise ValueError("Unknown source in daily batch")
    key = item.get("listingId")
    row = mapped.get(key)
    if row is None:
        raise ValueError("Unknown or unreviewed listing")
    for field in ("isin", "mic", "currency"):
        if item.get(field) != row[field]:
            raise ValueError("Unverified security, venue or currency")
    if source["identity"] != {k: True for k in ("isinMapped", "micMapped", "currencyVerified", "sessionCloseVerified")}:
        raise PermissionError("Source identity and session checks not completed")
    permitted_mics = set().union(*(PROVIDER_VENUE_MIC.get(v, set()) for v in source["venues"]))
    if not permitted_mics or item["mic"] not in permitted_mics:
        raise ValueError("Quote venue outside reviewed provider product scope")
    kind = item.get("quoteKind")
    if kind not in ALLOWED_KINDS:
        raise ValueError("Unknown quote kind")
    if source["observationKind"] == "alternative_venue_eod_candidate" and kind != "alternative_venue_eod":
        raise ValueError("Cboe alternative-venue price is not a primary official close")
    if kind == "primary_official_close" and not source["observationKind"].startswith("primary_venue"):
        raise ValueError("Primary official close requires a verified primary-venue source")
    if item.get("sessionVerified") is not True:
        raise ValueError("Actual completed local trading session not verified")
    try:
        day = date.fromisoformat(item["sessionDate"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("Invalid local session date") from None
    if day > now.date() or day < date(1990, 1, 1):
        raise ValueError("Future or implausible source session date")
    stamp = utc_stamp(item.get("publishedAt"))
    published = datetime.fromisoformat(stamp)
    if published > now + timedelta(hours=1) or published.date() < day - timedelta(days=1):
        raise ValueError("Provider publish date inconsistent with exchange session")
    if not https(item.get("sourceUrl")) or not https(item.get("sessionEvidenceUrl")):
        raise ValueError("Provider source and session proof must be HTTPS")
    amount = price(item.get("close"))
    volume = item.get("volume")
    if volume is not None and (type(volume) is not int or not 0 <= volume <= 10**13):
        raise ValueError("Invalid volume")
    evidence = {
        "listingId": key, "sourceId": source_id, "mic": row["mic"],
        "isin": row["isin"], "currency": row["currency"], "sessionDate": day.isoformat(),
        "close": amount, "volume": volume, "quoteKind": kind,
        "sourceUrl": item["sourceUrl"], "publishedAt": stamp,
        "sessionEvidenceUrl": item["sessionEvidenceUrl"]
    }
    digest = hashlib.sha256(json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return (key, source_id, row["mic"], row["isin"], row["currency"],
            day.isoformat(), amount, volume, kind, item["sourceUrl"],
            stamp, digest, now.isoformat(timespec="seconds"))


def ingest(db_path, source_id, batch, mappings, registry, inventory=None, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Offset-aware execution timestamp required")
    registry = validate_entitlements(registry)
    source = require_permission(source_id, "productionCollection", registry)
    require_permission(source_id, "privateRetention", registry)
    approved = reviewed_map(mappings, inventory)
    if not isinstance(batch, list) or not 1 <= len(batch) <= MAX_BATCH:
        raise ValueError("Bounded provider EOD batch required")
    clean = [validate_bar(x, source_id, approved, source, now) for x in batch]
    # Reject conflicting same-session rows before any durable database change.
    unique = {}
    for x in clean:
        key = (x[0], x[1], x[2], x[5])
        if key in unique and unique[key] != x:
            raise ValueError("Conflicting duplicate daily closes in one provider batch")
        unique[key] = x
    rows = list(unique.values())
    digest = hashlib.sha256(json.dumps(sorted(x[11] for x in rows)).encode()).hexdigest()
    dest = private_path(db_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(dest) as db:
        db.executescript(DML)
        with db:
            for x in rows:
                existing = db.execute(
                    "SELECT immutable_sha256 FROM eod_daily_close WHERE listing_id=? AND source_id=? AND mic=? AND session_date=?",
                    (x[0], x[1], x[2], x[5])).fetchone()
                if existing and existing[0] != x[11]:
                    raise ValueError("Provider correction requires explicit revision review: " + x[0] + " " + x[5])
                if not existing:
                    db.execute("INSERT INTO eod_daily_close VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", x)
            db.execute("INSERT OR IGNORE INTO eod_batch_receipt VALUES (?,?,?,?)",
                       (source_id, digest, now.isoformat(timespec="seconds"), len(rows)))
        return {"source": source_id, "input": len(batch), "unique": len(rows),
                "records": db.execute("SELECT COUNT(*) FROM eod_daily_close").fetchone()[0],
                "batchSha256": digest,
                "publicDisplayActivated": False,
                "note": "Private reviewed daily-close ledger; no public chart output and no new provider entitlement."}


def chart_rows(db_path, source_id, listing_id, registry):
    # Explicit separate publication right; no implicit right from collection/retention.
    registry = validate_entitlements(registry)
    source = require_permission(source_id, "publicDisplay", registry)
    require_permission(source_id, "privateRetention", registry)
    with sqlite3.connect(private_path(db_path)) as db:
        rows = db.execute(
            "SELECT session_date,close_decimal,volume,mic,currency,quote_kind,published_utc,original_source_url "
            "FROM eod_daily_close WHERE source_id=? AND listing_id=? ORDER BY session_date",
            (source_id, listing_id)).fetchall()
    # At least 2 actual session closes to draw a historical line; never invent missing days.
    if len(rows) < 2:
        return {"status": "not_enough_history", "listingId": listing_id, "bars": []}
    return {"status": "ok", "listingId": listing_id, "source": source["provider"],
            "product": source["product"], "bars": [
                {"date": d, "close": c, "volume": v, "mic": m, "currency": cur,
                 "kind": k, "publishedAt": t, "sourceUrl": u}
                for d, c, v, m, cur, k, t, u in rows
            ], "notice": "Licensed EOD observations only. Distinct venue sessions; not live quotes."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--batch", required=True, type=Path, help="Approved original provider JSONL only")
    p.add_argument("--listing-map", required=True, type=Path)
    p.add_argument("--source", required=True)
    p.add_argument("--private-db", required=True, type=Path)
    p.add_argument("--registry", type=Path, default=ROOT / "scripts/source_entitlements_v102.json")
    a = p.parse_args()
    if a.batch.stat().st_size > MAX_FILE_BYTES:
        p.error("Input exceeds batch size bound")
    payload = [json.loads(line) for line in a.batch.read_text().splitlines() if line.strip()]
    mapping = json.loads(a.listing_map.read_text())
    rights = load(a.registry)
    inventory = {r["id"] for r in json.loads((ROOT / "data/listing-coverage-v1.json").read_text())["records"]}
    print(json.dumps(ingest(a.private_db, a.source, payload, mapping, rights, inventory), sort_keys=True))


if __name__ == "__main__":
    main()
