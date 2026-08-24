"""Data sources. Everything here is free and needs no API key.

Deliberately no paid provider: the free tiers that cover European equities are
either useless (Alpha Vantage at 25 requests a day) or US-only (Finnhub free).
Yahoo's chart endpoint covers Oslo, Stockholm, XETRA, Paris and London with real
volume, and the Nordic regulators publish disclosures directly.

Those disclosure feeds are the good part. Companies are legally required to
publish material information to Oslo Børs NewsWeb and MFN before anywhere else,
so this reads the primary source rather than a news site's account of it.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

UA = "Mozilla/5.0 (compatible; stockwatch/1.0; +https://nordl.dev)"
TIMEOUT = 25


def _get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return response.read()


def chart(ticker: str, rng: str = "3mo", interval: str = "1d") -> dict | None:
    """Daily bars for a ticker. Yahoo suffixes: .OL Oslo, .ST Stockholm,
    .DE XETRA, .PA Paris, .L London, .CO Copenhagen, .HE Helsinki."""
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{urllib.parse.quote(ticker)}?range={rng}&interval={interval}"
    )
    try:
        payload = json.loads(_get(url))
    except Exception as error:                                  # noqa: BLE001
        print(f"  ! {ticker}: {error}")
        return None

    result = (payload.get("chart") or {}).get("result")
    if not result:
        return None
    block = result[0]
    quote = block["indicators"]["quote"][0]

    rows = []
    for i, ts in enumerate(block.get("timestamp") or []):
        close, volume = quote["close"][i], quote["volume"][i]
        if close is None or volume is None:
            continue                                            # holidays, halts
        rows.append(
            {
                "t": ts,
                "date": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d"),
                "open": quote["open"][i],
                "high": quote["high"][i],
                "low": quote["low"][i],
                "close": close,
                "volume": volume,
            }
        )
    if not rows:
        return None

    meta = block["meta"]
    return {
        "ticker": meta.get("symbol", ticker),
        "exchange": meta.get("fullExchangeName"),
        "currency": meta.get("currency"),
        "timezone": meta.get("exchangeTimezoneName"),
        "price": meta.get("regularMarketPrice"),
        "previousClose": meta.get("chartPreviousClose"),
        "bars": rows,
    }


def newsweb(count: int = 100) -> list[dict]:
    """Oslo Børs disclosures. The category matters more than the headline:
    REGULATORY means the company was legally obliged to publish it."""
    url = (
        "https://api3.oslo.oslobors.no/v1/newsreader/list"
        f"?category=&issuer=&fromDate=&toDate=&market=&messageTitle=&limit={count}"
    )
    try:
        payload = json.loads(_get(url))
    except Exception as error:                                  # noqa: BLE001
        print(f"  ! newsweb: {error}")
        return []

    out = []
    for message in (payload.get("data") or {}).get("messages", []):
        categories = message.get("category") or []
        labels = [c.get("category_en", "") for c in categories]
        out.append(
            {
                "source": "newsweb",
                "id": str(message.get("messageId")),
                "title": (message.get("title") or "").strip(),
                "issuer": (message.get("issuerSign") or message.get("issuerName") or "").strip(),
                "published": message.get("publishedTime"),
                "regulatory": any("NON-REGULATORY" not in l for l in labels) if labels else False,
                "categories": labels,
                "url": f"https://newsweb.oslobors.no/message/{message.get('messageId')}",
            }
        )
    return out


def mfn(count: int = 100) -> list[dict]:
    """MFN carries Nordic disclosures beyond Oslo - Stockholm especially."""
    try:
        root = ET.fromstring(_get("https://mfn.se/all/a.rss"))
    except Exception as error:                                  # noqa: BLE001
        print(f"  ! mfn: {error}")
        return []

    out = []
    for item in root.findall(".//item")[:count]:
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        author = (item.findtext("author") or "").strip()
        out.append(
            {
                "source": "mfn",
                "id": link or title,
                "title": title,
                "issuer": author,
                "published": (item.findtext("pubDate") or "").strip(),
                "regulatory": None,                             # MFN does not label it
                "categories": [],
                "url": link,
            }
        )
    return out
