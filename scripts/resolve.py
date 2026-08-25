"""Turn a list of company names into verified tickers.

Names are not tickers, and guessing from memory is how a watchlist ends up
quietly scanning the wrong instrument - or a delisted one that still returns a
stale price. Every candidate here is looked up, then fetched, and only kept if
real bars come back.

What it checks, and why each one has caught something:

  resolves     Yahoo's search knows the name at all
  is an equity funds, ETFs and indices resolve happily and have no company
               behind them: no filings, no news, nothing for a scanner to find
  has bars     a listing can exist and trade nothing
  liquidity    a volume spike on 400 shares a day is one retail order
  volatility   an instrument that never moves gives the scanner nothing

Run: python scripts/resolve.py names.txt
"""
from __future__ import annotations

import json
import statistics
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sources                                                    # noqa: E402

UA = "Mozilla/5.0 (compatible; stockwatch/1.0; +https://nordl.dev)"

# European venues, best first. A company listed in several places should be
# followed where it is domiciled: that is where its filings and its press are.
VENUE_RANK = {
    ".OL": 1, ".ST": 1, ".CO": 1, ".HE": 1, ".IC": 1,
    ".DE": 2, ".PA": 2, ".AS": 2, ".BR": 2, ".MI": 2, ".MC": 2, ".LS": 2,
    ".VI": 3, ".SW": 3, ".L": 3, ".F": 4, ".MU": 5, ".BE": 5, ".HM": 5,
    ".DU": 5, ".SG": 5, ".STU": 5, ".HA": 5,
}

# Quote types that are not a company.
NOT_A_COMPANY = {"ETF", "MUTUALFUND", "INDEX", "CURRENCY", "CRYPTOCURRENCY",
                 "FUTURE", "OPTION"}

# Below this a relative-volume signal is one retail order rather than a crowd.
# It is not a reason to drop a company - a small listing still files, and still
# gets written about - so it marks the row "thin" and scan.py withholds the
# volume alert for it. Price moves and news are unaffected.
THIN_BELOW = 20_000
MIN_BARS = 25

# Yahoo's search does not index every small Nordic listing: "Balder" never
# returns BALD-B.ST, and Eiendomsspar returns nothing at all. These are the
# symbols search cannot reach, and none of them is trusted on my say-so - each
# is fetched like any other candidate and dropped if no real bars come back.
OVERRIDES = {
    "balder": "BALD-B.ST",
    "austevoll seafood": "AUSS.OL",
    "caf": "CAF.MC",
    "eiendomsspar": "EIOF.OL",
    "heba fastigheter": "HEBA-B.ST",
    "daldrup & söhne": "4DS.DE",
    "formycon": "FYB.DE",
    "ivu traffic technologies": "IVU.DE",
    "iws": "IWS.OL",
    "wilh. wilhelmsen": "WWI.OL",
    "arctic fish": "AFISH.OL",
    "nordic halibut": "NOHAL.OL",
    "andfjord salmon": "ANDF.OL",
    "gerard perrier industrie": "PERR.PA",
    "ellos": "ELLOS.ST",
    "pelican aqua": "PLCAN.OL",
    "ice fish farm": "IFISH.OL",
    "prada": "1913.HK",
    "storebrand": "STB.OL",
    "frontline": "FRO.OL",
    # A group name matches its subsidiaries as readily as its parent, and the
    # subsidiary is often the busier line: "Siemens" reaches Siemens Energy and
    # Siemens Healthineers before Siemens AG, and "Tryg" reaches an Icelandic
    # insurer whose name merely contains the word.
    "siemens": "SIE.DE",
    "tryg": "TRYG.CO",
    # Odfjell SE, the chemical tanker owner, rather than Odfjell Drilling.
    "odfjell": "ODF.OL",
    # The carmaker, not the family holding company that owns part of VW.
    "porsche": "P911.DE",
}


def search(name: str, limit: int = 12) -> list[dict]:
    url = ("https://query2.finance.yahoo.com/v1/finance/search?q="
           + urllib.parse.quote(name)
           + f"&quotesCount={limit}&newsCount=0&listsCount=0")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read()).get("quotes", []) or []
    except Exception as error:                                    # noqa: BLE001
        print(f"  ! search {name}: {error}", file=sys.stderr)
        return []


def venue_rank(symbol: str) -> int:
    suffix = "." + symbol.split(".")[-1] if "." in symbol else ""
    return VENUE_RANK.get(suffix.upper(), 9 if suffix else 8)


def variants(name: str) -> list[str]:
    """Query forms to try. Yahoo matches on its own name for a company, which
    often carries or omits a legal suffix the user did not write - and does not
    always cope with accents."""
    import unicodedata
    forms = [name]
    stripped = name
    for suffix in (" Group", " Holding", " Holdings", " ASA", " AB", " A/S",
                   " AS", " SE", " NV", " SA", " plc", " Oyj", " AG"):
        if stripped.endswith(suffix):
            stripped = stripped[: -len(suffix)]
    if stripped != name:
        forms.append(stripped)
    folded = "".join(c for c in unicodedata.normalize("NFKD", name)
                     if not unicodedata.combining(c))
    folded = folded.replace("ø", "o").replace("Ø", "O").replace("æ", "ae").replace("å", "a")
    if folded != name:
        forms.append(folded)
    # A trailing common word can be the whole problem: "Tang og tare" is not a
    # listed name at all, but "Hoegh Autoliners" only fails on its vowel.
    if "&" in name:
        forms.append(name.replace("&", "and"))
    return list(dict.fromkeys(forms))


def candidates(name: str) -> list[dict]:
    """Plausible listings for a name, most promising venue first."""
    out = []
    seen_symbols = set()
    quotes = []
    for form in variants(name):
        quotes.extend(search(form))
        if any((q.get("quoteType") or "").upper() == "EQUITY" for q in quotes):
            break
    for q in quotes:
        symbol = q.get("symbol") or ""
        if not symbol or symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)
        kind = (q.get("quoteType") or "").upper()
        out.append({
            "symbol": symbol,
            "kind": kind,
            "longname": q.get("longname") or q.get("shortname") or "",
            "exchange": q.get("exchDisp") or q.get("exchange") or "",
            "rank": venue_rank(symbol),
        })
    out.sort(key=lambda c: (c["rank"], 0 if c["kind"] == "EQUITY" else 1))
    return out


def measure(symbol: str) -> dict | None:
    """Real bars, or nothing."""
    data = sources.chart(symbol, rng="6mo")
    if not data or len(data["bars"]) < MIN_BARS:
        return None
    bars = data["bars"]
    volumes = [b["volume"] for b in bars if b["volume"]]
    if not volumes:
        return None
    returns = [(b["close"] - a["close"]) / a["close"]
               for a, b in zip(bars, bars[1:]) if a["close"]]
    if len(returns) < 20:
        return None
    daily = statistics.pstdev(returns)
    return {
        "ticker": data["ticker"],
        "exchange": data["exchange"],
        "currency": data["currency"],
        "medianVolume": int(statistics.median(volumes)),
        "annualVolPct": round(daily * (252 ** 0.5) * 100, 1),
        "twoSigmaDays": sum(1 for r in returns if abs(r) > 2 * daily),
        "bars": len(bars),
    }


def resolve(name: str) -> dict:
    """One name to one verified listing, with a reason when there is not one."""
    override = OVERRIDES.get(name.lower().strip())
    if override:
        measured = measure(override)
        if measured:
            return {"name": name, "status": "ok", "longname": name,
                    "via": "override", "venues": 1,
                    "thin": measured["medianVolume"] < THIN_BELOW, **measured}
        # An override that does not verify is worth saying out loud rather than
        # falling back silently to whatever search returns.
        print(f"  ! override {name} -> {override} has no data", file=sys.stderr)

    options = candidates(name)
    if not options:
        return {"name": name, "status": "not found"}

    # A name that only ever resolves to a fund is not a company. Say so rather
    # than silently following an ETF that will never file anything.
    if all(c["kind"] in NOT_A_COMPANY for c in options):
        kinds = sorted({c["kind"] for c in options})
        return {"name": name, "status": "not a company",
                "detail": f"resolves only to {', '.join(kinds).lower()}",
                "symbol": options[0]["symbol"]}

    # Every equity candidate is measured, not just the first with data. A
    # company can be quoted on half a dozen venues and most of them trade
    # nothing: Frontline shows 300 shares a day on a German secondary listing
    # and 4 million in Oslo. Stopping at the first result that answers picks
    # whichever venue Yahoo happened to name first and calls the company
    # illiquid.
    tried, measured_all = [], []
    for option in options[:8]:
        if option["kind"] in NOT_A_COMPANY:
            continue
        tried.append(option["symbol"])
        measured = measure(option["symbol"])
        if measured:
            measured_all.append((measured, option))

    if not measured_all:
        return {"name": name, "status": "no price data",
                "detail": "tried " + ", ".join(tried[:5])}

    # Home venue first, volume only to break ties within it.
    #
    # Ranking by volume alone looks right and is wrong for this tool. Frontline
    # trades more in New York than Oslo, Balder more on the London IOB than in
    # Stockholm - and following them there would cost exactly what the scanner
    # is for: NewsWeb and MFN match on Nordic tickers, and home_language reads
    # the venue suffix to decide which language to read the press in. A
    # Norwegian company followed as a US listing gets neither.
    #
    # It also picks the wrong company outright: on volume, "CAF" resolves to a
    # Morgan Stanley China fund on the NYSE rather than the Spanish train
    # builder in Madrid.
    measured_all.sort(key=lambda pair: (pair[1]["rank"], -pair[0]["medianVolume"]))
    best, option = measured_all[0]
    return {"name": name, "status": "ok", "longname": option["longname"],
            "venues": len(measured_all),
            "thin": best["medianVolume"] < THIN_BELOW, **best}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    names = [line.strip() for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.startswith("#")]
    print(f"Resolving {len(names)} names\n")

    started = time.time()
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(resolve, names))

    by_status: dict[str, list[dict]] = {}
    for r in results:
        by_status.setdefault(r["status"], []).append(r)

    for status in ("ok", "not a company", "no price data", "not found"):
        rows = by_status.get(status, [])
        if not rows:
            continue
        print(f"\n=== {status.upper()} ({len(rows)}) ===")
        for r in sorted(rows, key=lambda x: x["name"].lower()):
            if status == "ok":
                mark = "thin" if r.get("thin") else "    "
                print(f"  {mark} {r['name']:<26} {r['ticker']:<13} {r['exchange']:<15} "
                      f"vol {r['annualVolPct']:>5}%  {r['medianVolume']:>10,}/day  "
                      f"{r['twoSigmaDays']:>2} big")
            else:
                print(f"  {r['name']:<28} {r.get('detail', '')}")

    out = Path(__file__).resolve().parent.parent / "data" / "resolved.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\n{len(by_status.get('ok', []))} of {len(names)} usable, "
          f"in {time.time() - started:.0f}s -> {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
