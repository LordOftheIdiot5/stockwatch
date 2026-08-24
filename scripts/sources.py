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


# --- open web news ----------------------------------------------------------
# The regulated feeds carry what a company is obliged to say. This carries what
# everyone else is saying about it, which is where an analyst downgrade, a
# contract win reported by the counterparty, or a sector story shows up first.

SOURCE_WEIGHT = {
    # Wires and papers that break things.
    "reuters": 3, "bloomberg": 3, "financial times": 3, "ft.com": 3,
    "wall street journal": 3, "cnbc": 2, "the guardian": 2, "bbc": 2,
    # Nordic press.
    "e24": 3, "dagens næringsliv": 3, "dn.no": 3, "nrk": 2, "aftenposten": 2,
    "di.se": 3, "dagens industri": 3, "svd": 2, "borsen": 2, "berlingske": 2,
    "hegnar": 2, "finansavisen": 3, "kapital": 2, "yle": 2, "helsingin sanomat": 2,
    # Trade press worth reading.
    "upstream": 2, "tradewinds": 2, "intrafish": 2, "offshore energy": 2,
    "mining.com": 1, "renewables now": 1,
    # Content farms. Present in results, rarely worth a push notification.
    "marketbeat": -3, "zacks": -2, "simply wall st": -3, "insider monkey": -3,
    "tipranks": -2, "benzinga": -1, "stocktwits": -3, "investing.com": -1,
    "marketscreener": -1, "tradingview": -2, "barchart": -2, "gurufocus": -3,
}

# Words that mark a story as consequential rather than commentary.
MATERIAL = {
    3: ("acquire", "acquisition", "merger", "takeover", "bid for", "buyout",
        "profit warning", "guidance cut", "guidance raise", "bankruptcy",
        "insolven", "fraud", "investigation", "lawsuit", "recall", "strike",
        "explosion", "accident", "shutdown", "halted", "resign", "steps down",
        "oppkjøp", "fusjon", "gransking", "søksmål", "konkurs"),
    2: ("contract", "order", "wins", "awarded", "upgrade", "downgrade",
        "price target", "results", "earnings", "quarterly", "dividend",
        "buyback", "capital markets day", "ceo", "cfo", "chair",
        "kontrakt", "ordre", "oppgrader", "nedgrader", "resultat", "utbytte"),
    1: ("agreement", "partnership", "expansion", "launch", "approval",
        "avtale", "samarbeid", "lansering", "godkjen"),
}

# Headlines that are algorithmic filler whatever the source.
JUNK = (
    "shares gap", "what's next", "etfs investing", "shares sold by",
    "shares bought by", "position lowered", "position raised", "stake in",
    "short interest", "trading down", "trading up", "reaches new",
    "should you buy", "is it time to", "hidden gem", "price prediction",
    # Generated market-wrap filler: a headline about nothing having happened.
    "holds steady", "holds above", "masks a deeper", "quiet monday",
    "quiet session", "little changed", "flat as", "in focus as investors",
)


def _news_score(title: str, source: str) -> int:
    """Higher means more likely to matter. Negative means noise."""
    lowered = title.lower()
    if any(j in lowered for j in JUNK):
        return -5
    score = SOURCE_WEIGHT.get((source or "").lower().strip(), 0)
    for weight, words in MATERIAL.items():
        if any(w in lowered for w in words):
            score += weight
            break
    return score


def news(query: str, count: int = 25) -> list[dict]:
    """Open-web coverage of a company, scored for whether it is worth reading."""
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(f'"{query}"')
           + "&hl=en-GB&gl=GB&ceid=GB:en")
    try:
        root = ET.fromstring(_get(url))
    except Exception as error:                                   # noqa: BLE001
        print(f"  ! news {query}: {error}")
        return []

    out = []
    for item in root.findall(".//item")[:count]:
        title = (item.findtext("title") or "").strip()
        node = item.find("{*}source")
        source = node.text if node is not None else ""
        # Google appends " - Source" to titles; drop it for cleanliness.
        clean = title.rsplit(" - ", 1)[0] if source and title.endswith(f"- {source}") else title
        out.append({
            "source": "web",
            "id": (item.findtext("link") or title),
            "title": clean,
            "publisher": source,
            "published": (item.findtext("pubDate") or "").strip(),
            "url": (item.findtext("link") or "").strip(),
            "score": _news_score(clean, source),
        })
    return out
