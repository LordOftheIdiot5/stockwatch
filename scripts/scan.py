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
NEWS_PER_TICKER = 2       # a flood about one name is still a flood
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

def stem(w):
    """Crude suffix strip. 'upgrades'/'upgrade' and 'discoveries'/'discovery'
    are one word to a reader and must be one token here."""
    for suf in ("ingen","ies","ing","ene","ed","es","er","en","s"):
        if len(w) - len(suf) >= 3 and w.endswith(suf):
            w = w[:-len(suf)] + ("y" if suf == "ies" else "")
            break
    # A silent trailing 'e' survives suffix-stripping on one side only:
    # 'upgrades' -> 'upgrad' but 'upgrade' -> 'upgrade'. Drop it from both.
    return w[:-1] if len(w) >= 5 and w.endswith("e") else w

# The same event gets reported in different words. These are the equity-news
# synonyms frequent enough to be worth collapsing; each maps to one token so
# "raises outlook" and "lifts guidance" become the same three tokens.
SYNONYM = {
    "lift": "rais", "hik": "rais", "boost": "rais", "upgrad": "rais",
    "increas": "rais", "hev": "rais", "oppjuster": "rais",
    "lower": "cut", "slash": "cut", "reduc": "cut", "downgrad": "cut",
    "trim": "cut", "kutt": "cut", "nedjuster": "cut",
    "outlook": "guidanc", "forecast": "guidanc", "prognos": "guidanc",
    "utsikt": "guidanc", "guidance": "guidanc",
    "acquir": "acq", "acquisit": "acq", "takeov": "acq", "buyout": "acq",
    "merg": "acq", "oppkjop": "acq", "kjop": "acq",
    "halt": "stop", "suspend": "stop", "shutdown": "stop", "clos": "stop",
    "stans": "stop", "steng": "stop",
    "separation": "split", "separat": "split", "demerg": "split",
    "spinoff": "split", "spin": "split", "divid": "split",
    "profit": "earning", "result": "earning", "quart": "earning",
    "resultat": "earning", "kvartal": "earning",
}


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
    return ("rais" in a and "cut" in b) or ("cut" in a and "rais" in b)


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


def main() -> int:
    watchlist = load_watchlist()
    seen = load_seen()
    now = datetime.now(timezone.utc)

    print(f"Scanning {len(watchlist)} tickers at {now:%Y-%m-%d %H:%M} UTC")

    quotes, alerts, rows_pending = [], [], []
    for entry in watchlist:
        ticker = entry["ticker"]
        data = sources.chart(ticker)
        if not data:
            continue
        measured = score(data["bars"])
        if not measured:
            continue

        row = {
            "ticker": data["ticker"],
            "name": entry.get("name", data["ticker"]),
            "exchange": data["exchange"],
            "currency": data["currency"],
            **measured,
        }
        quotes.append(row)

        rows_pending.append(row)

    # The market baseline is the watchlist's own median move. If everything is up
    # three percent, a stock up four has moved one - and that is what gets scored.
    day_moves = [r["changePct"] for r in rows_pending]
    market = statistics.median(day_moves) if day_moves else 0.0
    print(f"  market baseline: median move {market:+.2f}%")

    for row in rows_pending:
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
                "kind": "price",
                "key": key,
                "ticker": row["ticker"],
                "name": row["name"],
                "headline": " and ".join(reasons),
                "url": f"https://finance.yahoo.com/quote/{row['ticker']}",
                "fresh": key not in seen,
                **measured,
            })
            seen.add(key)

    # Disclosures, matched to the watchlist by ticker.
    symbols = {e["ticker"].split(".")[0].upper(): e for e in watchlist}
    disclosures = sources.newsweb(120) + sources.mfn(80)
    # What has already been reported for each name, so the same event is not
    # told three times: once by the filing, once by its English translation,
    # and once by the wire that picked it up.
    told: dict[str, list[str]] = {}
    for item in disclosures:
        symbol = (item.get("issuer") or "").upper() or ticker_from_title(item["title"])
        if not symbol or symbol not in symbols:
            continue
        if is_routine(item["title"]):
            continue
        entry = symbols[symbol]
        subject = entry.get("name") or entry["ticker"]
        prior = told.setdefault(entry["ticker"], [])
        # Companies file the same disclosure in Norwegian and English.
        if same_story(item["title"], prior, subject):
            continue
        prior.append(item["title"])
        key = f"news:{item['source']}:{item['id']}"
        alerts.append({
            "kind": "disclosure",
            "key": key,
            "ticker": symbols[symbol]["ticker"],
            "name": symbols[symbol].get("name", symbol),
            "headline": item["title"],
            "regulatory": item.get("regulatory"),
            "url": item["url"],
            "published": item.get("published"),
            "fresh": key not in seen,
        })
        seen.add(key)

    # Open-web coverage, one query per name. The regulated feeds say what the
    # company had to say; this catches what everyone else said about it - a
    # downgrade, a counterparty announcing the same contract, a sector story.
    for entry in watchlist:
        query = entry.get("name") or entry["ticker"]
        # Seeded with this name's disclosures: a wire report of a filing already
        # shown is the same story, whichever feed carried it first.
        accepted = told.setdefault(entry["ticker"], [])
        taken = 0
        for item in sources.news(query, 25):
            if not sources.worth_alerting(item):
                continue
            # A daily buyback tally is routine wherever it is published. This
            # filter only ran on disclosures, so buyback stories arrived by the
            # open web instead - which is how ASML's did.
            if is_routine(item["title"]):
                continue
            if hours_old(item.get("published", "")) > NEWS_MAX_AGE_H:
                continue
            if same_story(item["title"], accepted, query):
                continue
            if taken >= NEWS_PER_TICKER:
                break
            accepted.append(item["title"])
            taken += 1
            key = f"web:{item['id']}"
            alerts.append({
                "kind": "news",
                "key": key,
                "ticker": entry["ticker"],
                "name": query,
                "headline": item["title"],
                "publisher": item.get("publisher"),
                "score": item["score"],
                "url": item["url"],
                "published": item.get("published"),
                "fresh": key not in seen,
            })
            seen.add(key)

    fresh = [a for a in alerts if a["fresh"]]
    quotes.sort(key=lambda q: -q["rvol"])

    DATA.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps({
        "generated": now.isoformat(timespec="seconds"),
        "tickers": len(watchlist),
        "quotes": quotes,
        "alerts": sorted(alerts, key=lambda a: (not a["fresh"], a["kind"])),
    }, indent=1), encoding="utf-8")
    save_seen(seen)

    print(f"  {len(quotes)} quotes, {len(alerts)} alerts, {len(fresh)} of them new")
    for a in fresh:
        if a["kind"] == "news":
            mark = f"+{a['score']}"
        elif a.get("regulatory"):
            mark = "REG"
        else:
            mark = "   "
        print(f"  [{mark:^3}] {a['ticker']:<12} {a['headline'][:66]}")

    # Hand the fresh ones to the workflow so it can decide whether to shout.
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"fresh={len(fresh)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
