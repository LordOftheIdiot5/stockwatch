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
    "motley fool": -3, "247 wall st": -3, "24/7 wall st": -3, "invezz": -2,
    "ad-hoc-news": -2, "newsfilecorp": -2, "globenewswire": -1, "accesswire": -2,
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
        # A company changing what it expects to earn is among the most
        # consequential things it says, and the phrasing varies far more than
        # the two exact strings the top tier lists. Translation routes every
        # language through these words, so they have to be the loose ones.
        "forecast", "outlook", "guidance", "raises its", "lifts its",
        "cuts its", "lowers its", "expects to", "warns",
        "kontrakt", "ordre", "oppgrader", "nedgrader", "resultat", "utbytte",
        "prognose", "utsikter", "varsler"),
    1: ("agreement", "partnership", "expansion", "launch", "approval",
        "avtale", "samarbeid", "lansering", "godkjen"),
}

# Headlines that are algorithmic filler whatever the source.
JUNK = (
    "shares gap", "what's next", "etfs investing", "shares sold by",
    "shares bought by", "position lowered", "position raised", "stake in",
    "short interest", "trading down", "trading up", "reaches new",
    "should you buy", "is it time to", "hidden gem", "price prediction",
    # Valuation commentary. Nothing happened; someone did arithmetic on a chart.
    "trades at a", "discount to its", "premium to its", "% discount",
    "% upside", "fair value", "undervalued", "overvalued", "worth buying",
    "here's why", "heres why", "what to know", "things to watch",
    # Generated market-wrap filler: a headline about nothing having happened.
    "holds steady", "holds above", "masks a deeper", "quiet monday",
    "quiet session", "little changed", "flat as", "in focus as investors",
    # The Nordic equivalent: a daily column about which way the index went.
    # "KOMMENTAR:" and "MARKNADSKOMMENTAR" prefix them by convention.
    "kommentar:", "marknadskommentar", "borskommentar", "børskommentar",
    "loftet oslo bors", "løftet oslo børs", "oslo børs fredag",
    "oslo børs mandag", "stockholmsborsen", "stockholmsbörsen steg",
    "dette skjer i dag", "dagens aksjer", "morgenrapport", "vinnere og tapere",
)


def _flatten(name: str) -> str:
    """Publisher names arrive in whatever form Google has: 'marketscreener.com',
    'simplywall.st', 'FT.com'. Exact-match lookup misses all of those, so the
    weight table silently did nothing for them. Compare on letters alone."""
    return "".join(c for c in (name or "").lower() if c.isalnum())


_WEIGHTS = tuple((_flatten(k), v) for k, v in SOURCE_WEIGHT.items())


def _material(title: str) -> int:
    """How consequential the event is, from the words alone: 3 is an acquisition
    or a profit warning, 1 is a partnership, 0 is commentary."""
    lowered = title.lower()
    for weight in sorted(MATERIAL, reverse=True):
        if any(w in lowered for w in MATERIAL[weight]):
            return weight
    return 0


def _source_weight(source: str) -> int:
    flat = _flatten(source)
    # Longest key first, so 'financial times' is not shadowed by a shorter key.
    return next((v for k, v in sorted(_WEIGHTS, key=lambda kv: -len(kv[0]))
                 if k and k in flat), 0)


def _news_score(title: str, source: str) -> int:
    """Kept as a single number for ranking and display. The alert decision uses
    worth_alerting, which does not collapse the two axes."""
    if any(j in title.lower() for j in JUNK):
        return -5
    return _source_weight(source) + _material(title)


def rescore(item: dict, english: str | None) -> dict:
    """Re-judge an item on its English text.

    The keyword lists are English. Judging a Finnish headline against them asks
    whether a Finnish sentence contains the word "acquisition", which it never
    does - so every foreign story scored zero on materiality and was held to the
    standard of a story with no event in it. Scoring the translation instead
    means one vocabulary covers every language.
    """
    text = english or item["title"]
    item["english"] = english
    item["material"] = _material(text)
    item["sourceWeight"] = _source_weight(item.get("publisher", ""))
    item["junk"] = any(j in text.lower() for j in JUNK) or         any(j in item["title"].lower() for j in JUNK)
    item["score"] = -5 if item["junk"] else item["material"] + item["sourceWeight"]
    return item


def worth_reading(item: dict) -> bool:
    """Whether a story earns a place under its company on the page.

    Looser than worth_alerting, because the page and the notification are not
    the same audience. Someone who has clicked a company's name wants the
    coverage; someone whose phone buzzed wants the event. Four accounts of one
    oil alliance are worth reading together and are not worth four buzzes.
    """
    if item.get("junk"):
        return False
    material, source = item.get("material", 0), item.get("sourceWeight", 0)
    if material >= 1:
        return source > -3
    return source >= 1


def worth_alerting(item: dict) -> bool:
    """Whether a story earns a place on the page.

    Materiality and source quality are judged separately, because adding them
    let a weak publisher veto a real event. SEB upgrading Sandvik to buy with a
    445-krone target is a fact whoever prints it - and only aggregators printed
    it, because wires do not cover single-broker notes on mid-caps. Summed, that
    story scored 1 against a threshold of 2 and vanished.

    So: the bigger the event, the less the publisher matters. A takeover clears
    on anything but a known farm. A story with no material content at all has to
    come from a wire, or it is someone's opinion.
    """
    if item.get("junk"):
        return False
    material, source = item.get("material", 0), item.get("sourceWeight", 0)
    if material >= 3:
        return source > -3          # a takeover is news from all but a farm
    if material >= 2:
        return source >= -2         # an upgrade or a contract needs an outlet
    if material >= 1:
        return source >= 2          # a partnership needs a real newsroom
    return source >= 3              # no event named: only a wire is worth it


# Google News is a different newspaper in every locale. Asking it in English
# only returns the English-speaking world's account of a Norwegian company,
# which is thinner and later than the Norwegian one - and for a company that no
# English outlet covers, it returns nothing at all.
LOCALES = {
    "en": ("en-GB", "GB", "GB:en"), "no": ("no", "NO", "NO:no"),
    "sv": ("sv", "SE", "SE:sv"),    "da": ("da", "DK", "DK:da"),
    "fi": ("fi", "FI", "FI:fi"),    "de": ("de", "DE", "DE:de"),
    "fr": ("fr", "FR", "FR:fr"),    "nl": ("nl", "NL", "NL:nl"),
    "es": ("es", "ES", "ES:es"),    "it": ("it", "IT", "IT:it"),
    "pt": ("pt-PT", "PT", "PT:pt-150"), "pl": ("pl", "PL", "PL:pl"),
}

# A company's home market reports it first and in most detail, so the listing
# venue decides which language to ask in beyond English.
HOME_LANGUAGE = {
    ".OL": "no", ".ST": "sv", ".CO": "da", ".HE": "fi", ".DE": "de",
    ".F": "de", ".SW": "de", ".VI": "de", ".PA": "fr", ".BR": "fr",
    ".AS": "nl", ".MC": "es", ".MI": "it", ".LS": "pt", ".WA": "pl",
    ".L": "en", ".IR": "en", "": "en",
}


def home_language(ticker: str) -> str:
    suffix = "." + ticker.split(".")[-1] if "." in ticker else ""
    return HOME_LANGUAGE.get(suffix.upper(), "en")


# Google's locale is where a story was served, not what language it is in. The
# Danish feed carries Norwegian papers, the Norwegian feed carries English wires.
# Translating Norwegian as Danish mostly works - they are that close - but the
# label shown to a reader should say what the headline actually is.
_MARKERS = {
    "no": (" ikke ", " ikkje ", " og ", " på ", " til ", " fra ", " som ", " har ",
           " skal ", " kroner", " milliarder", " selskapet", "øre", "kjøp"),
    "da": (" ikke ", " og ", " på ", " til ", " fra ", " som ", " har ", " kroner",
           " milliarder", " selskabet", " virksomhed", " mia."),
    "sv": (" inte ", " och ", " på ", " till ", " från ", " som ", " har ",
           " kronor", " miljarder", " bolaget", " köp", " ökar"),
    "de": (" der ", " die ", " das ", " und ", " für ", " mit ", " von ", " auf ",
           " nicht ", " milliarden", " aktie"),
    "fr": (" le ", " la ", " les ", " des ", " pour ", " avec ", " sur ", " dans ",
           " milliards"),
    "nl": (" het ", " een ", " van ", " voor ", " met ", " niet ", " miljard"),
    "es": (" el ", " la ", " los ", " las ", " para ", " con ", " por ", " millones"),
    "it": (" il ", " la ", " di ", " per ", " con ", " che ", " miliardi"),
    "fi": (" ja ", " on ", " ei ", " että ", " miljardia", " yhtiö"),
    "en": (" the ", " and ", " for ", " with ", " from ", " that ", " billion ",
           " million ", " after ", " says "),
}

# Danish and Norwegian share almost every function word, so these are the ones
# that actually separate them. Without this every Norwegian headline served by
# the Danish feed would be labelled Danish.
_NO_ONLY = ("olje", "nytt", "sjef", "ikkje", "sokkel", "norsk", "gjør",
            "milliarder kroner", "øre", " mye ", " nå ", "selskapet", "kjøp")
_DA_ONLY = ("olie", "selskab", "virksomhed", "mia. kr", "dansk", "erhverv",
            "øget", "chef", " nyt ", "ligeledes")


def detect_language(title: str, fallback: str) -> str:
    """Best guess at the language of a headline, falling back to the locale it
    was served from. Cheap on purpose - this decides a badge, not a decision."""
    lowered = title.lower()
    padded = f" {lowered} "

    # Norwegian and Danish first, and before the function-word test rather than
    # after it. They share almost every function word, so the test that tells
    # them apart is the vocabulary - and a headline can carry that tell while
    # containing no function word at all: "Oljetoppens drom: et nytt Castberg"
    # scored zero on every marker list and fell straight through to whichever
    # feed had served it.
    #
    # Substrings, not whole words, because Norwegian compounds freely: the tell
    # is inside "Oljetoppens", not standing beside it.
    no_hits = sum(1 for m in _NO_ONLY if m in lowered)
    da_hits = sum(1 for m in _DA_ONLY if m in lowered)
    if no_hits != da_hits and max(no_hits, da_hits) > 0:
        return "no" if no_hits > da_hits else "da"

    scores = {code: sum(1 for m in markers if m in padded)
              for code, markers in _MARKERS.items()}
    best = max(scores, key=lambda c: scores[c])
    if scores[best] == 0:
        return fallback
    # A tie between the two means neither gave itself away; trust the feed.
    if best in ("no", "da") and fallback in ("no", "da"):
        return fallback
    return best


def news(query: str, count: int = 25, locale: str = "en") -> list[dict]:
    """Open-web coverage of a company in one locale."""
    hl, gl, ceid = LOCALES.get(locale, LOCALES["en"])
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(f'"{query}"')
           + f"&hl={hl}&gl={gl}&ceid={ceid}")
    try:
        root = ET.fromstring(_get(url))
    except Exception as error:                                   # noqa: BLE001
        print(f"  ! news {query} [{locale}]: {error}")
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
            "lang": detect_language(clean, locale),
            "servedFrom": locale,
            "id": (item.findtext("link") or title),
            "title": clean,
            "publisher": source,
            "published": (item.findtext("pubDate") or "").strip(),
            "url": (item.findtext("link") or "").strip(),
            "score": _news_score(clean, source),
            "material": _material(clean),
            "sourceWeight": _source_weight(source),
            "junk": any(j in clean.lower() for j in JUNK),
        })
    return out


def news_everywhere(queries: list[tuple[str, list[str]]], count: int = 40,
                    workers: int = 12) -> dict[str, list[dict]]:
    """Every company in every language it is likely to be written about.

    Concurrent because it is otherwise the slowest part of a scan by far: ten
    companies across eight locales is eighty requests, five seconds together and
    over a minute in sequence. Google serves these without complaint at this
    rate; the limit here is politeness, not throughput.
    """
    from concurrent.futures import ThreadPoolExecutor

    jobs = [(name, locale) for name, locales in queries for locale in locales]
    out: dict[str, list[dict]] = {name: [] for name, _ in queries}

    def one(job: tuple[str, str]) -> tuple[str, list[dict]]:
        name, locale = job
        return name, news(name, count, locale)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for name, items in pool.map(one, jobs):
            out[name].extend(items)
    return out
