"""Scan the watchlist and emit signals.

Two rules govern what counts as a signal, and both exist to stop this becoming
a noise generator:

1. Everything is measured against the instrument's own recent behaviour. A 4%
   move means nothing for a small-cap biotech and a lot for a utility, so moves
   are scored in standard deviations rather than percent. Volume is scored
   against a rolling *median*, because a mean that includes last week's spike
   quietly raises the bar for noticing the next one.

2. A disclosure only matters if it is new. Every run records what it has already
   seen, so a headline is reported once and then stops shouting.
"""
from __future__ import annotations

import json
import os
import re
import statistics
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sources                                                   # noqa: E402
from translate import Translator                                  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SEEN_PATH = DATA / "seen.json"
OUT_PATH = DATA / "signals.json"

# Thresholds. Deliberately not tuned - nothing here has been backtested yet, so
# these are starting points to be measured, not settings that are known to work.
RVOL_ALERT = 2.5          # times the 20-day median volume
MOVE_SIGMA = 2.0          # standard deviations of daily return
BASELINE_DAYS = 20
# Materiality and source quality are weighed separately in sources.py; see
# worth_alerting there for why a single summed threshold could not work.
NEWS_MAX_AGE_H = 48       # older than this is history, not an alert
NEWS_PER_TICKER = 6       # enough to read under a company, not a flood
# A story worth reading under a company is not automatically worth interrupting
# someone for. Four accounts of one oil alliance belong on the page together;
# only the one that names the event belongs in a notification.
ALERT_MATERIAL = 2
NEWS_PER_LOCALE = 40      # how deep to read each language's feed
# SHARED_MIN, below, replaced a similarity threshold that could not work.
MAX_SEEN = 4000

# Disclosures a company is obliged to file but which carry no information. Left
# visible in the data and kept out of alerts, because a feed that shouts about
# daily buyback tallies trains you to stop reading it.
ROUTINE = (
    "buy-back", "buyback", "tilbakekj", "acquisition of own shares",
    "egne aksjer", "nokkelinformasjon", "nøkkelinformasjon",
    "finansiell kalender", "financial calendar", "share capital and votes",
    "aksjekapital og stemmer", "weekly report", "ukesrapport",
)


def is_routine(title: str) -> bool:
    lowered = title.lower()
    return any(marker in lowered for marker in ROUTINE)


def load_watchlist() -> list[dict]:
    return json.loads((ROOT / "watchlist.json").read_text(encoding="utf-8"))["tickers"]


def load_seen() -> set[str]:
    if SEEN_PATH.exists():
        return set(json.loads(SEEN_PATH.read_text(encoding="utf-8")))
    return set()


def save_seen(seen: set[str]) -> None:
    DATA.mkdir(exist_ok=True)
    SEEN_PATH.write_text(json.dumps(sorted(seen)[-MAX_SEEN:]), encoding="utf-8")


def score(bars: list[dict]) -> dict | None:
    """Relative volume and a volatility-normalised return for the latest bar."""
    if len(bars) < BASELINE_DAYS + 2:
        return None

    latest, prior = bars[-1], bars[-2]
    history = bars[-(BASELINE_DAYS + 1):-1]

    volumes = [b["volume"] for b in history if b["volume"]]
    median_volume = statistics.median(volumes) if volumes else 0
    rvol = latest["volume"] / median_volume if median_volume else 0

    returns = []
    for a, b in zip(history, history[1:]):
        if a["close"]:
            returns.append((b["close"] - a["close"]) / a["close"])
    sigma = statistics.pstdev(returns) if len(returns) > 2 else 0
    change = (latest["close"] - prior["close"]) / prior["close"] if prior["close"] else 0
    z = change / sigma if sigma else 0

    return {
        "date": latest["date"],
        "close": round(latest["close"], 4),
        "changePct": round(change * 100, 2),
        "sigma": round(z, 2),
        "volume": latest["volume"],
        "medianVolume": int(median_volume),
        "rvol": round(rvol, 2),
    }


# --- telling one story from another -------------------------------------------
# Comparing headlines by shared words does not work here, and the failure is
# measurable: "SEB upgrades Sandvik to buy" and "Sandvik climbs after SEB
# upgrade" - the same event - overlap 0.077, exactly as much as Infineon's
# acquisition overlaps its guidance cut, which are different events. No
# threshold separates those, so the comparison itself had to change.
#
# Four changes, each aimed at a case that was getting it wrong:
#   accent folding   so "Vaar" and "Vår" are one word, and Norwegian headlines
#                    tokenise at all - the old [a-zA-Z] pattern dropped them
#   stemming         so "upgrades" and "upgrade" meet
#   synonyms         so "raises outlook" and "lifts guidance" meet
#   drop the subject every headline from a per-company query names the company,
#                    so the name says nothing about which story this is
#
# And two vetoes, because the errors are not symmetric: a surviving duplicate
# costs a line, a wrong merge deletes a story you needed to see.
#
# Known limit: English and Norwegian headlines with no shared cognate - "Q2
# results beat expectations" against "kvartalsresultat over forventningene" -
# are not matched. That needs a dictionary. It fails toward showing both.

STOP = {"with","from","that","this","into","over","after","will","than","have",
        "been","more","said","says","about","their","they","its","for","and",
        "the","are","was","were","has","new","not","but","all","can"}

def fold(text):
    """Accent-fold so Norwegian and its transliteration meet: vår/vaar -> var."""
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.replace("ø","o").replace("æ","ae").replace("ß","ss").replace("aa","a")

# Suffixes safe to remove from a word of any length.
_SUFFIX = ("ingen", "ing", "ene", "ed", "en")

# These need length behind them. Swedish, Norwegian and Danish attach the
# definite article to the noun, so "kvartal" and "kvartalet" are one word - two
# Swedish reports of one chairman-fee cut stayed separate until "-et" came off.
# But "-et" also ends "target", "market" and "budget", and "-er" ends "order".
# The Scandinavian compounds that carry the article are long; the English words
# they collide with are six letters or fewer.
_SUFFIX_LONG = ("erna", "arna", "arne", "ion", "et", "er")
_LONG_FROM = 7


def stem(w):
    """Plural first, then at most one further suffix.

    The order is what makes this idempotent. Stripping suffixes in a single
    undifferentiated pass gives one word two stems - "orders" loses its "s" and
    stops at "order", while "order" goes on to lose "er" and reaches "ord".
    Repeating the pass instead is worse: "raises" would fall through "rais" to
    "rai" while "raise" stops at "rais". Taking the plural off first means both
    forms enter the second stage identical, so they must leave it identical.
    """
    if len(w) > 3 and w.endswith("s"):
        w = w[:-1]
        if len(w) > 3 and w.endswith("ie"):        # companies -> company
            w = w[:-2] + "y"
    pool = (_SUFFIX_LONG + _SUFFIX) if len(w) >= _LONG_FROM else _SUFFIX
    for suf in pool:
        if len(w) - len(suf) >= 3 and w.endswith(suf):
            w = w[:-len(suf)]
            break
    # A silent trailing 'e' survives on one side only: 'upgrades' -> 'upgrad'
    # but 'upgrade' -> 'upgrade'. Drop it from both.
    return w[:-1] if len(w) >= 5 and w.endswith("e") else w


# The same event gets reported in different words. These are the equity-news
# synonyms frequent enough to be worth collapsing, so that "raises outlook" and
# "lifts guidance" reduce to the same tokens.
#
# Written as whole words, not stems, and put through the stemmer below. Hand
# written stems rot: nine of them were silently unreachable, and "stans" - the
# stem of Norwegian "stanser" - is not even its own stem. Words cannot rot,
# because the stemmer is the same one the headlines go through.
# Named, because the polarity veto below has to refer to them and a loose
# string drifted once already: the canon was renamed and the veto kept looking
# for the old token, silently merging a guidance raise with a guidance cut.
RAISE, CUT = "raise", "cut"

SYNONYM_WORDS = {
    RAISE: ("lifts", "hikes", "boosts", "upgrades", "increases", "raises",
              "hever", "oppjusterer", "hojer", "hoyer", "okar", "oker",
              "hojner"),
    CUT: ("lowers", "slashes", "reduces", "downgrades", "trims", "cutter",
          "kutter", "nedjusterer", "senker", "sanker", "saenker", "sanka",
          "reduserer", "reducerer", "minskar"),
    "guidance": ("outlook", "forecast", "prognose", "utsikter", "guidance"),
    "acq": ("acquires", "acquisition", "takeover", "buyout", "merger",
            "oppkjop", "kjoper", "koper", "forvarv", "overtagelse"),
    "stop": ("halts", "suspends", "shutdown", "closes", "stanser", "stenger",
             "stopper", "lukker"),
    "split": ("separation", "separates", "demerger", "spinoff", "delning",
              "utskillelse"),
    "earnings": ("profit", "results", "quarter", "resultat", "kvartal",
                 "rapport", "earnings"),
}

# Built by running every word through the same stemmer the headlines use, so a
# key cannot be unreachable by construction.
SYNONYM = {stem(fold(w)): canon
           for canon, words in SYNONYM_WORDS.items() for w in words}


def tokens(title):
    out = set()
    for word in re.findall(r"[a-z0-9]{3,}", fold(title)):
        if word in STOP:
            continue
        root = stem(word)
        out.add(SYNONYM.get(root, root))
    return out

def distinctive(title, subject):
    """Drop the company's own name. Every headline from a per-company query
    mentions it, so it says nothing about which story this is."""
    drop = tokens(subject) | {"group","asa","ab","nv","plc","technologies","aktiebolag"}
    return tokens(title) - drop

SHARED_MIN = 2

# Two vetoes, because a wrong merge is worse than a duplicate: a duplicate
# wastes a line, a wrong merge deletes a story you needed to see.

def _proper(title, subject):
    """Capitalised words that are not the company and not sentence-initial.
    Place and entity names: Tertre, Sluiskil, Balder, C2i."""
    drop = tokens(subject)
    found = set()
    for word in re.findall(r"[A-Za-zÀ-ÿ0-9]+", title):
        if word[:1].isupper() and len(word) >= 3:
            token = stem(fold(word))
            if token not in drop and token not in STOP:
                found.add(token)
    return found


def _opposed(a, b):
    """A guidance raise and a guidance cut are never the same story, however
    much wording they share."""
    return (RAISE in a and CUT in b) or (CUT in a and RAISE in b)


def same_story(title, others, subject):
    mine = distinctive(title, subject)
    if len(mine) < SHARED_MIN:
        return False
    my_names = _proper(title, subject)
    for other in others:
        theirs = distinctive(other, subject)
        if len(mine & theirs) < SHARED_MIN or _opposed(mine, theirs):
            continue
        their_names = _proper(other, subject)
        # Both name places or entities, and none in common: different events.
        if my_names and their_names and not (my_names & their_names):
            continue
        return True
    return False


def hours_old(published: str) -> float:
    """Google News gives RFC 822 dates. Anything unparseable is treated as old."""
    from email.utils import parsedate_to_datetime
    try:
        when = parsedate_to_datetime(published)
    except Exception:                                            # noqa: BLE001
        return 1e6
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - when).total_seconds() / 3600


def ticker_from_title(title: str) -> str | None:
    """MFN puts the ticker in the headline rather than a field: 'PNO: Q2 report'."""
    match = re.match(r"^([A-Z0-9\-]{2,10}):", title.strip())
    return match.group(1) if match else None


def locales_for(entry: dict, extra: list[str]) -> list[str]:
    """Which languages to ask about this company in.

    Its home market always, because that is where it is covered first and in
    most detail. English always, because that is where the wires are. Anything
    else the watchlist asks for.
    """
    if entry.get("locales"):
        return list(entry["locales"])
    return sorted({sources.home_language(entry["ticker"]), "en"} | set(extra))


def spark(bars: list[dict], points: int = 30) -> list[float]:
    """Closes for a sparkline."""
    return [round(b["close"], 4) for b in bars[-points:] if b["close"]]


def main() -> int:
    config = json.loads((ROOT / "watchlist.json").read_text(encoding="utf-8"))
    watchlist = config["tickers"]
    extra = config.get("extraLocales", [])
    seen = load_seen()
    now = datetime.now(timezone.utc)
    translator = Translator()

    print(f"Scanning {len(watchlist)} tickers at {now:%Y-%m-%d %H:%M} UTC")

    # --- prices ---------------------------------------------------------
    companies: list[dict] = []
    for entry in watchlist:
        data = sources.chart(entry["ticker"])
        if not data:
            continue
        measured = score(data["bars"])
        if not measured:
            continue
        companies.append({
            "ticker": data["ticker"],
            "name": entry.get("name", data["ticker"]),
            "exchange": data["exchange"],
            "currency": data["currency"],
            "spark": spark(data["bars"]),
            "stories": [],
            **measured,
        })

    # The market baseline is the watchlist's own median move. If everything is
    # up three percent, a stock up four has moved one - and that is what counts.
    market = statistics.median([c["changePct"] for c in companies]) if companies else 0.0
    print(f"  market baseline: median move {market:+.2f}%")

    alerts: list[dict] = []
    for row in companies:
        row["marketPct"] = round(market, 2)
        row["excessPct"] = round(row["changePct"] - market, 2)
        sigma_day = abs(row["changePct"] / row["sigma"]) if row["sigma"] else 0
        row["excessSigma"] = round(row["excessPct"] / sigma_day, 2) if sigma_day else 0
        reasons = []
        if row["rvol"] >= RVOL_ALERT:
            reasons.append(f"volume {row['rvol']}x its 20-day median")
        if abs(row["excessSigma"]) >= MOVE_SIGMA:
            direction = "up" if row["excessSigma"] > 0 else "down"
            reasons.append(
                f"{direction} {abs(row['excessPct'])}% against a {market:+.2f}% market "
                f"({abs(row['excessSigma'])} sigma)"
            )
        if reasons:
            key = f"px:{row['ticker']}:{row['date']}"
            alerts.append({
                "kind": "price", "key": key, "ticker": row["ticker"],
                "name": row["name"], "headline": " and ".join(reasons),
                "url": f"https://finance.yahoo.com/quote/{row['ticker']}",
                "fresh": key not in seen,
            })
            seen.add(key)

    by_ticker = {c["ticker"]: c for c in companies}

    # --- regulated disclosures ------------------------------------------
    symbols = {e["ticker"].split(".")[0].upper(): e for e in watchlist}
    told: dict[str, list[str]] = {}
    for item in sources.newsweb(120) + sources.mfn(80):
        symbol = (item.get("issuer") or "").upper() or ticker_from_title(item["title"])
        if not symbol or symbol not in symbols:
            continue
        if is_routine(item["title"]):
            continue
        entry = symbols[symbol]
        ticker = entry["ticker"]
        if ticker not in by_ticker:
            continue
        subject = entry.get("name") or ticker
        lang = sources.home_language(ticker)
        # Filings arrive in Norwegian and English; compare on English so both
        # forms of one filing land together.
        english = translator.english(item["title"], lang)
        prior = told.setdefault(ticker, [])
        compare = english or item["title"]
        if same_story(compare, prior, subject):
            continue
        prior.append(compare)

        key = f"news:{item['source']}:{item['id']}"
        story = {
            "kind": "disclosure", "key": key,
            "headline": item["title"],
            "english": english if english != item["title"] else None,
            "lang": lang,
            "regulatory": item.get("regulatory"),
            "url": item["url"], "published": item.get("published"),
            "publisher": "Regulated filing",
            "material": 3,
            "fresh": key not in seen,
        }
        by_ticker[ticker]["stories"].append(story)
        alerts.append({**story, "ticker": ticker, "name": subject})
        seen.add(key)

    # --- open web, in every language ------------------------------------
    queries = [(e.get("name") or e["ticker"], locales_for(e, extra)) for e in watchlist]
    print(f"  fetching {sum(len(l) for _, l in queries)} feeds "
          f"across {len(queries)} companies")
    harvest = sources.news_everywhere(queries, count=NEWS_PER_LOCALE)
    print(f"  {sum(len(v) for v in harvest.values())} raw items")

    for entry in watchlist:
        ticker = entry["ticker"]
        if ticker not in by_ticker:
            continue
        subject = entry.get("name") or ticker
        accepted = told.setdefault(ticker, [])
        kept = 0
        # Freshest first, so the earliest account of a story is the one kept.
        items = sorted(harvest.get(subject, []),
                       key=lambda i: hours_old(i.get("published", "")))
        within_language: dict[str, list[str]] = {}

        for item in items:
            if kept >= NEWS_PER_TICKER:
                break
            if hours_old(item.get("published", "")) > NEWS_MAX_AGE_H:
                continue
            if is_routine(item["title"]):
                continue
            # Cheap pass first: duplicates inside one language are recognised
            # without translation, and most duplicates are here.
            same_lang = within_language.setdefault(item["lang"], [])
            if same_story(item["title"], same_lang, subject):
                continue
            same_lang.append(item["title"])

            english = translator.english(item["title"], item["lang"])
            sources.rescore(item, english)
            if not sources.worth_reading(item):
                continue
            # Then across languages, on English, where one event reported in
            # eight markets finally collapses to one line.
            compare = english or item["title"]
            if same_story(compare, accepted, subject):
                continue
            accepted.append(compare)
            kept += 1

            key = f"web:{item['id']}"
            story = {
                "kind": "news", "key": key,
                "headline": item["title"],
                "english": english if english != item["title"] else None,
                "lang": item["lang"],
                "publisher": item.get("publisher"),
                "score": item["score"], "material": item["material"],
                "url": item["url"], "published": item.get("published"),
                "fresh": key not in seen,
            }
            by_ticker[ticker]["stories"].append(story)
            if item["material"] >= ALERT_MATERIAL:
                alerts.append({**story, "ticker": ticker, "name": subject})
            seen.add(key)

    translator.save()
    print(f"  {translator.report()}")

    fresh = [a for a in alerts if a["fresh"]]
    companies.sort(key=lambda c: -c["rvol"])
    for c in companies:
        c["stories"].sort(key=lambda s: (not s["fresh"], -(s.get("material") or 0)))

    DATA.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "generated": now.isoformat(timespec="seconds"),
        "tickers": len(watchlist),
        "marketPct": round(market, 2),
        "languages": sorted({l for _, ls in queries for l in ls}),
        "companies": companies,
        "alerts": sorted(alerts, key=lambda a: (not a["fresh"], a["kind"])),
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    save_seen(seen)

    stories = sum(len(c["stories"]) for c in companies)
    print(f"  {len(companies)} companies, {stories} stories, "
          f"{len(alerts)} alerts, {len(fresh)} of them new")
    for a in fresh:
        tag = "REG" if a.get("regulatory") else (a.get("lang") or "px").upper()[:3]
        print(f"  [{tag:^3}] {a['ticker']:<12} {a['headline'][:62]}")

    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"fresh={len(fresh)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
