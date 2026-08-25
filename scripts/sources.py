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


def worth_translating(item: dict) -> bool:
    """Whether a foreign headline is worth spending allowance on.

    Materiality cannot be judged before translation, but two things can. A
    headline matching the junk patterns is filler in any language, and a
    publisher at the bottom of the weight table can never clear worth_reading
    whatever the story turns out to be. Both were being translated and then
    thrown away, which on a monthly allowance is the difference between paying
    for what gets shown and paying for what does not.
    """
    if any(j in item["title"].lower() for j in JUNK):
        return False
    return _source_weight(item.get("publisher", "")) > -3


def promise(item: dict) -> tuple:
    """Sort key for spending a limited allowance on the best candidates first:
    a better publisher, then a fresher story."""
    return (-_source_weight(item.get("publisher", "")), item.get("_age", 0))


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
# The publisher is the last resort, not the first: a Danish outlet writing in
# English would otherwise have its English filed as Danish. It settles the case
# nothing else can - a headline with no function word in it at all.
PUBLISHER_LANGUAGE = {
    "no": ("e24", "dn.no", "dagens naringsliv", "finansavisen", "nrk",
           "aftenposten", "hegnar", "kapital", "energiwatch.no", "sysla",
           "tu.no", "nettavisen", "vg.no", "adressa", "bt.no", "shifter",
           "kyst.no", "finanswatch.no", "intrafish.no", "petro.no", "ilaks"),
    "da": ("borsen.dk", "berlingske", "jyllands-posten", "politiken",
           "finans.dk", "shippingwatch", "energiwatch.dk", "medwatch",
           "dr.dk", "tv2.dk", "euroinvestor"),
    "sv": ("di.se", "dagens industri", "svd", "affarsvarlden", "dagens ps",
           "placera", "privata affarer", "realtid", "svt.se", "nyteknik",
           "borsvarlden", "aktiespararna"),
    "de": ("boerse.de", "handelsblatt", "manager magazin", "wirtschaftswoche",
           "faz.net", "ad-hoc-news", "finanznachrichten", "boersennews",
           "der aktionar", "onvista"),
    "fr": ("les echos", "la tribune", "boursorama", "zonebourse", "bfmtv",
           "le figaro", "abcbourse"),
    "nl": ("fd.nl", "het financieele dagblad", "beursduivel", "iex.nl",
           "nu.nl", "belegger.nl"),
    "fi": ("kauppalehti", "helsingin sanomat", "talouselama", "yle.fi",
           "arvopaperi"),
    "es": ("expansion", "cinco dias", "el economista", "eleconomista",
           "bolsamania", "invertia"),
    "it": ("il sole 24 ore", "milano finanza", "soldionline"),
}

_PUBLISHER_LANGUAGE = tuple(
    (_flatten(name), code)
    for code, names in PUBLISHER_LANGUAGE.items() for name in names)


def language_of_publisher(publisher: str) -> str | None:
    flat = _flatten(publisher)
    if not flat:
        return None
    # Longest first so a short key cannot shadow a more specific one.
    for name, code in sorted(_PUBLISHER_LANGUAGE, key=lambda kv: -len(kv[0])):
        if name and name in flat:
            return code
    return None


_MARKERS = {
    "no": (" ikke ", " ikkje ", " og ", " på ", " til ", " fra ", " som ", " har ",
           " skal ", " kroner", " milliarder", " selskapet", " etter ", " med "),
    "da": (" ikke ", " og ", " på ", " til ", " fra ", " som ", " har ", " kroner",
           " milliarder", " selskabet", " virksomhed", " mia.", " efter "),
    "sv": (" inte ", " och ", " på ", " till ", " från ", " som ", " har ",
           " kronor", " miljarder", " bolaget", " efter ", " med "),
    "de": (" der ", " die ", " das ", " und ", " für ", " mit ", " von ", " auf ",
           " nicht ", " milliarden", " aktie", " im ", " zum "),
    "fr": (" le ", " la ", " les ", " des ", " pour ", " avec ", " sur ", " dans ",
           " milliards", " une ", " est "),
    "nl": (" het ", " een ", " van ", " voor ", " met ", " niet ", " miljard",
           " naar ", " bij "),
    "es": (" el ", " la ", " los ", " las ", " para ", " con ", " por ", " millones",
           " una ", " del "),
    "it": (" il ", " la ", " di ", " per ", " con ", " che ", " miliardi", " una ",
           " del "),
    # No " on " here. It is the Finnish "is", and also an English preposition,
    # so it made "Boom Lasting on Power Needs" score Finnish.
    "fi": (" ja ", " ei ", " että ", " sekä ", " mukaan ", " kertoo ", " kertoi ",
           " miljoonaa ", " miljardia ", " yhtiö", " osake", " tulos"),
    "en": (" the ", " and ", " for ", " with ", " from ", " that ", " to ", " in ",
           " of ", " on ", " as ", " at ", " by ", " is ", " are ", " was ",
           " after ", " says ", " said ", " over ", " its ", " under ", " into ",
           " amid ", " ahead ", " against ", " million ", " billion ", " shares ",
           " stock ", " quarter ", " profit ", " revenue ", " deal ", " reports "),
}

# Danish and Norwegian share almost every function word, so these are the ones
# that actually separate them - and they are matched as substrings, because
# Norwegian compounds freely and the tell is inside "Oljetoppens".
# Norwegian against Danish. Not " mot ": Swedish uses it too, which is how
# "AI testas mot viltolyckor pa jarnvagen" came out Norwegian.
_NO_ONLY = (" å ", " enn ", "frykter", "svakere", "sterkere", "ikkje",
            "olje", "nytt", "sjef", "sokkel", "norsk", "gjør", "høst",
            "milliarder kroner", " mye ", " nå ", "selskapet", "kjøp")
_DA_ONLY = (" mod ", "frygter", "svagere", "stærkere", "olie", "selskab",
            "virksomhed", "mia. kr", "dansk", "erhverv", "øget", "chef",
            " nyt ", "ligeledes", "efterår", " også ")
_SV_ONLY = (" och ", " inte ", " är ", " kronor", " bolaget", " ökar", " än ",
            " sedan ", "järnväg", "svensk", "köp", "höjer", "sänker")

SCANDINAVIAN = ("no", "da", "sv")


def _scandinavian(lowered: str, fallback: str, publisher: str = "") -> str:
    """Which of Norwegian, Danish and Swedish.

    Spelling settles this better than grammar does. Swedish writes a-diaeresis
    and o-diaeresis where Norwegian and Danish write ae and o-slash, and the
    three share so much vocabulary that a headline can otherwise carry no clue
    at all. One letter in "jarnvagen" says Swedish more reliably than any word
    in the sentence.
    """
    swedish_letters = sum(lowered.count(c) for c in "äö")
    nordic_letters = sum(lowered.count(c) for c in "æø")
    if swedish_letters and not nordic_letters:
        return "sv"

    no_hits = sum(1 for m in _NO_ONLY if m in lowered)
    da_hits = sum(1 for m in _DA_ONLY if m in lowered)
    sv_hits = sum(1 for m in _SV_ONLY if m in lowered)

    if nordic_letters and not swedish_letters:
        # Norwegian or Danish, so Swedish evidence is not evidence.
        if no_hits != da_hits:
            return "no" if no_hits > da_hits else "da"
        # The two write the same sentence. Who printed it is the only thing
        # left to go on, and it is a good thing to go on.
        known = language_of_publisher(publisher)
        if known in ("no", "da"):
            return known
        return fallback if fallback in ("no", "da") else "no"

    best = max((no_hits, "no"), (da_hits, "da"), (sv_hits, "sv"))
    ties = sum(1 for n in (no_hits, da_hits, sv_hits) if n == best[0])
    if best[0] > 0 and ties == 1:
        return best[1]
    known = language_of_publisher(publisher)
    if known in SCANDINAVIAN:
        return known
    return fallback if fallback in SCANDINAVIAN else best[1]

# Enough English function words to be sure rather than lucky.
_SURE_ENGLISH = 2


def detect_language(title: str, fallback: str, publisher: str = "") -> str:
    """Best guess at the language of a headline.

    The order matters more than any individual test.

    English first, because a Danish or Norwegian outlet writing in English is
    common and the publisher would otherwise mislabel it: MedWatch is Danish
    and files "ALK CFO to receive DKK 25m payout" in English.

    Then the Norwegian-Danish vocabulary test, which is the pair no function
    word can separate.

    Then the full marker count, but only when one language wins outright.

    The publisher last, and only when the words gave nothing away - which is
    exactly the case it was added for, a Norwegian headline served by the
    Danish feed with no function word in it at all.
    """
    lowered = title.lower()
    padded = f" {lowered} "

    english = sum(1 for m in _MARKERS["en"] if m in padded)
    if english >= _SURE_ENGLISH:
        return "en"

    # Spelling is decisive between the Scandinavian three and costs nothing to
    # look at, so it comes before counting function words they share.
    # Only when there is Scandinavian evidence to weigh. Entering this branch
    # merely because the feed was Scandinavian sent an English headline served
    # by the Danish feed straight to a Danish verdict without ever counting a
    # word: "Novo Nordisk's acquisition spree marred by several failed deals".
    scand_letters = any(c in lowered for c in "æøäå")
    scand_markers = max(sum(1 for m in _MARKERS[c] if m in padded)
                        for c in SCANDINAVIAN)
    if scand_letters or scand_markers > 0:
        other = max(sum(1 for m in _MARKERS[c] if m in padded)
                    for c in _MARKERS if c not in SCANDINAVIAN and c != "en")
        if scand_markers >= other or any(c in lowered for c in "æø"):
            return _scandinavian(lowered, fallback, publisher)

    scores = sorted(((sum(1 for m in ms if m in padded), code)
                     for code, ms in _MARKERS.items()), reverse=True)
    if scores[0][0] > 0 and scores[0][0] > scores[1][0]:
        return scores[0][1]

    known = language_of_publisher(publisher)
    if known:
        return known
    return fallback


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
            "lang": detect_language(clean, locale, source),
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


# --- short selling ----------------------------------------------------------
# Finanstilsynet publishes every disclosed net short position in a Norwegian
# instrument, free and without a key. Anything at or above 0.5% of share capital
# must be reported, so the register is a complete picture of the part of short
# interest that is public - and it is a different kind of signal from price,
# volume or news: it is what professionals have actually put money behind.
#
# Sweden and Denmark publish the same data under the same EU rule, but behind
# pages that build themselves in the browser rather than an endpoint a scan can
# read. Norway is 36 of the names on this list, so it is worth having alone.

_SSR_URL = "https://ssr.finanstilsynet.no/api/v2/instruments"

# Words that identify an industry rather than a company. Matching on these puts
# Andfjord Salmon's short interest under Salmon Evolution.
_GENERIC = {"salmon", "seafood", "fish", "farm", "farming", "bank", "energy",
            "offshore", "shipping", "group", "holding", "holdings", "asa", "as",
            "ltd", "limited", "international", "norge", "norway", "nordic"}


def _issuer_key(name: str) -> str:
    import re
    import unicodedata
    folded = "".join(c for c in unicodedata.normalize("NFKD", name.lower())
                     if not unicodedata.combining(c))
    folded = folded.replace("ø", "o").replace("æ", "ae").replace("å", "a")
    words = [w for w in re.findall(r"[a-z0-9]+", folded)
             if w not in {"asa", "as", "a/s", "sa", "se", "nv", "plc", "ab",
                          "oyj", "ag", "holding", "holdings", "group", "ltd",
                          "limited"}]
    return " ".join(words)


def short_positions() -> dict[str, dict]:
    """Disclosed net short positions, keyed by a normalised issuer name.

    Each entry carries the latest disclosed percentage and the one before it,
    so a change can be reported rather than a level - a name sitting at 2% for
    a year is not news, and a move from 0.6% to 2% is.
    """
    try:
        payload = json.loads(_get(_SSR_URL))
    except Exception as error:                                   # noqa: BLE001
        print(f"  ! short register: {error}")
        return {}

    out = {}
    for instrument in payload:
        events = sorted(instrument.get("events") or [], key=lambda e: e.get("date") or "")
        if not events:
            continue
        latest = events[-1]
        previous = events[-2] if len(events) > 1 else None
        # activePositions is the list of funds holding the position, not a
        # count of them - each with its own percentage and name. Who is short
        # is more interesting than how many, so keep the largest and the count
        # rather than the whole array, which would bloat every scan's output.
        positions = sorted(latest.get("activePositions") or [],
                           key=lambda h: -(h.get("shortPercent") or 0))
        out[_issuer_key(instrument.get("issuerName", ""))] = {
            "issuer": instrument.get("issuerName"),
            "isin": instrument.get("isin"),
            "percent": latest.get("shortPercent"),
            "previous": previous.get("shortPercent") if previous else None,
            "date": (latest.get("date") or "")[:10],
            "holders": len(positions),
            "largest": (positions[0].get("positionHolder") if positions else None),
            "largestPercent": (positions[0].get("shortPercent") if positions else None),
        }
    return out


def match_short(name: str, register: dict[str, dict]) -> dict | None:
    """Find a company in the register without matching on its industry.

    Token overlap is too loose here: "Andfjord Salmon" and "Salmon Evolution"
    share a word that describes what they farm, not who they are, and the naive
    match reported one company's short interest under the other's name.
    """
    key = _issuer_key(name)
    if not key:
        return None
    if key in register:
        return register[key]
    # One name may carry a qualifier the other omits - "Yara" against "Yara
    # International" - but only as a whole leading phrase, never a shared word.
    for other, entry in register.items():
        if other.startswith(key + " ") or key.startswith(other + " "):
            return entry
    return None
