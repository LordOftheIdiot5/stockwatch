"""Collect source-dated original Nasdaq Nordic RSS notice metadata.

This is an unlinked exchange-level stream, not a company-specific disclosure.
Only original title, publication timestamp and source link are stored. There
are no article bodies, copied attachments or numeric prices in this dataset.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from defusedxml import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = "data/nasdaq-nordic-notices.json"
SOURCE_PAGE = "https://subscribe.news.eu.nasdaq.com/rss"
FEEDS = {
    "nordicInvestorNews": ("https://api.news.eu.nasdaq.com/news/rss/nasdaqNordicNews", "Nordic investor & press releases"),
    "nordicExchangeNotices": ("https://api.news.eu.nasdaq.com/news/rss/mainMarketNotices", "Nordic exchange notices"),
}
LINK_HOSTS = {"view.news.eu.nasdaq.com", "api.news.eu.nasdaq.com", "www.nasdaq.com"}
MAX_BYTES = 600_000
MAX_PER_FEED = 125
MAX_ITEMS = 1000
RETENTION_DAYS = 180


def utc(value):
    if not isinstance(value, str):
        return None
    try:
        d = parsedate_to_datetime(value)
    except (ValueError, TypeError, IndexError):
        try:
            d = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d.astimezone(timezone.utc) if d.tzinfo else None


def iso(d):
    return d.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def allowed(url):
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == "https" and parsed.hostname in LINK_HOSTS
                and not parsed.username and not parsed.password
                and parsed.port in (None, 443) and len(url) <= 1800)
    except (TypeError, ValueError):
        return False


def retrieve(url):
    if url not in (value[0] for value in FEEDS.values()):
        raise ValueError("unknown_feed_endpoint")
    req = Request(url, headers={
        "User-Agent": "Nordl-Stockwatch/1.0 (+https://stocks.nordl.dev/)",
        "Accept": "application/rss+xml, application/xml;q=0.9"})
    with urlopen(req, timeout=18) as response:
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("rss_over_byte_limit")
    return raw


def parse(feed_key, raw, now):
    if feed_key not in FEEDS:
        raise ValueError("unknown_feed")
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ValueError("invalid_rss_size")
    root = ET.fromstring(raw)
    if root.tag != "rss":
        raise ValueError("not_rss")
    rows = {}
    for item in root.findall("./channel/item")[:MAX_PER_FEED]:
        title = " ".join((item.findtext("title") or "").split()).strip()
        link = (item.findtext("link") or "").strip()
        when = utc((item.findtext("pubDate") or "").strip())
        if (not title or len(title) > 280 or not allowed(link) or not when
                or when < now-timedelta(days=RETENTION_DAYS)
                or when > now+timedelta(minutes=5)):
            continue
        key = "nasdaq:"+hashlib.sha256(link.encode("utf-8")).hexdigest()
        rows[key] = {
            "id": key, "title": title, "published": iso(when),
            "url": link, "feed": feed_key, "category": FEEDS[feed_key][1],
            "publisher": "Nasdaq Nordic", "issuerMatch": "not_established",
            "regulatory": None,
        }
    return list(rows.values())


def build(root=ROOT, now=None, fetch=retrieve):
    now = now or datetime.now(timezone.utc)
    dst = root/OUTPUT
    try:
        previous = json.loads(dst.read_text(encoding="utf8"))
    except (OSError, ValueError):
        previous = {}
    existing = {}
    for row in previous.get("items") or []:
        if (isinstance(row, dict) and str(row.get("id", "")).startswith("nasdaq:")
                and allowed(row.get("url")) and utc(row.get("published"))
                and now-timedelta(days=RETENTION_DAYS) <= utc(row["published"]) <= now):
            existing[row["id"]] = row
    sources = {}
    for key, (url, label) in FEEDS.items():
        prior = (previous.get("sources") or {}).get(key) or {}
        state = {"url": url, "label": label, "lastAttempt": iso(now),
                 "lastSuccess": prior.get("lastSuccess")}
        try:
            received = parse(key, fetch(url), now)
            existing.update({row["id"]: row for row in received})
            state.update({"status": "ok", "received": len(received),
                          "lastSuccess": iso(now)})
        except Exception as error:
            state.update({"status": "error", "received": 0,
                          "errorType": type(error).__name__})
        sources[key] = state
    rows = sorted(existing.values(), key=lambda x: (x["published"], x["id"]), reverse=True)[:MAX_ITEMS]
    result = {
        "schemaVersion": 1, "generated": iso(now), "sourcePage": SOURCE_PAGE,
        "status": "ok" if all(x["status"] == "ok" for x in sources.values()) else "degraded",
        "sources": sources, "items": rows,
        "notice": "Original Nasdaq Nordic RSS titles, timestamps and outbound links only. No issuer association, article body, original price or resale rights inferred. Retained notices do not mean the feed recently succeeded."
    }
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf8")
    tmp.replace(dst)
    print("Nasdaq Nordic RSS:", len(rows), "notices,",
          sum(v["status"] == "ok" for v in sources.values()), "of", len(sources), "feeds succeeded")
    return result


if __name__ == "__main__":
    build()
