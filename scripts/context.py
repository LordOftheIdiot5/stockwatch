"""Market context around the watchlist: commodities, freight, and share-class spreads.

Three things the company scan cannot see on its own.

COMMODITIES exist because several rows on the watchlist are a leveraged bet on
one number. Bluelake is nickel, copper and zinc; the shipping names are crude;
the grid names are power and aluminium. A drill result matters differently
depending on what the metal did that week, and the scan had no way to know.

FREIGHT is the honest compromise here. The Baltic indices - BDI, BDTI, BCTI -
are the real measure and they are a licensed commercial product; there is no
free feed and this does not pretend otherwise. What is free is the ETFs that
hold freight futures: BDRY for dry bulk and BWET for tankers track the forward
curve directly, so they move with rates rather than with shipping equities.
They are a proxy. They carry roll cost and tracking error, and on any given day
they can diverge from spot rates. Labelled as proxies in the output so nobody
reads them as the index.

SHARE-CLASS SPREADS are the narrowest feature here, and deliberately so. Of the
Swedish A/B pairs on this list only Investor has both classes quoted with a
spread wide enough to be worth watching; Volvo's two classes track each other
to within about 0.15%, which is inside the cost of switching. The rest have no
A share on Yahoo at all - most Swedish A shares are closely held and never
trade. So this reports a spread and where it sits in its own history. It does
not tell anyone to switch, because whether that is worth doing depends on tax
treatment, on holding period, on whether the votes matter to the holder, and on
a spread being able to stay unusual for a very long time.
"""

from __future__ import annotations

import json
import statistics
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (compatible; stockwatch/1.0; +https://nordl.dev)"
TIMEOUT = 25
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/"

# Grouped the way someone reading the watchlist would want them: the metals a
# miner is exposed to, then energy, then the freight proxies.
COMMODITIES = [
    ("GC=F", "Gold", "metals", "USD/oz"),
    ("SI=F", "Silver", "metals", "USD/oz"),
    ("HG=F", "Copper", "metals", "USD/lb"),
    ("ZNC=F", "Zinc", "metals", "USD/t"),
    ("ALI=F", "Aluminium", "metals", "USD/t"),
    ("PL=F", "Platinum", "metals", "USD/oz"),
    ("PA=F", "Palladium", "metals", "USD/oz"),
    # Nickel has no free spot feed that holds up. JJN quotes on a short window
    # and goes empty over a year, so it is unusable here. NIKL is the closest
    # available thing and it is miners rather than metal - equity beta, not the
    # price of nickel - so it is flagged proxy and named for what it is. Worth
    # carrying anyway: Bluelake's largest deposit is nickel, and nothing else
    # on this page speaks to it at all.
    ("NIKL", "Nickel miners", "metals", "USD", True),
    ("TIO=F", "Iron ore 62% Fe", "metals", "USD/t"),
    ("BZ=F", "Brent crude", "energy", "USD/bbl"),
    ("CL=F", "WTI crude", "energy", "USD/bbl"),
    ("NG=F", "Natural gas", "energy", "USD/MMBtu"),
    ("URA", "Uranium (ETF)", "energy", "USD"),
]

# Proxies, not indices. See the module docstring.
FREIGHT = [
    ("BDRY", "Dry bulk freight", "tracks dry bulk futures"),
    ("BWET", "Tanker freight", "tracks tanker futures"),
    ("BOAT", "Shipping equities", "global shipping companies"),
]

# Only pairs where both classes actually quote and the spread is wide enough to
# see. Adding a pair whose classes track to 0.1% would produce a signal that is
# always inside the cost of acting on it.
SHARE_CLASSES = [
    ("INVE-A.ST", "INVE-B.ST", "Investor"),
    ("VOLV-A.ST", "VOLV-B.ST", "Volvo"),
]


def _chart(ticker: str, rng: str = "1y", interval: str = "1d") -> dict | None:
    url = f"{CHART}{urllib.parse.quote(ticker)}?range={rng}&interval={interval}"
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        payload = json.loads(urllib.request.urlopen(request, timeout=TIMEOUT).read())
    except Exception as error:                                   # noqa: BLE001
        print(f"  ! {ticker}: {error}")
        return None
    result = (payload.get("chart") or {}).get("result")
    return result[0] if result else None


def _quote(ticker: str) -> dict | None:
    """Last price plus one-day and one-month change."""
    data = _chart(ticker)
    if not data:
        return None
    closes = [c for c in (data["indicators"]["quote"][0].get("close") or []) if c]
    if not closes:
        return None

    # Everything is derived from this one series, deliberately. Mixing
    # meta.regularMarketPrice with the closes array produced gold up 31% in a
    # day and a year position of 384 out of 100: for continuous futures the
    # meta price and the historical series are not on the same contract, so
    # comparing across them is meaningless rather than merely imprecise.
    last = closes[-1]
    previous = closes[-2] if len(closes) > 1 else last

    def pct(reference):
        return round((last / reference - 1) * 100, 2) if reference else None

    # Roughly a month of trading days back, or the oldest point available.
    month_ago = closes[-22] if len(closes) >= 22 else closes[0]
    year_low, year_high = min(closes), max(closes)

    return {
        "last": round(float(last), 4),
        "changePct": pct(previous),
        "monthPct": pct(month_ago),
        # Where it sits in its own year, which says more than a percentage:
        # 0 is the low, 100 the high.
        "yearPosition": (
            round((last - year_low) / (year_high - year_low) * 100)
            if year_high > year_low else None
        ),
        "yearLow": round(float(year_low), 4),
        "yearHigh": round(float(year_high), 4),
    }


def commodities() -> list[dict]:
    out = []
    for entry in COMMODITIES:
        ticker, name, group, unit = entry[:4]
        proxy = entry[4] if len(entry) > 4 else False
        quote = _quote(ticker)
        if quote:
            row = {"ticker": ticker, "name": name, "group": group,
                   "unit": unit, **quote}
            if proxy:
                # Same badge the freight rows carry, for the same reason: the
                # reader has to be able to tell a price from a stand-in.
                row["proxy"] = True
            out.append(row)
    return out


def freight() -> list[dict]:
    out = []
    for ticker, name, note in FREIGHT:
        quote = _quote(ticker)
        if quote:
            out.append({"ticker": ticker, "name": name, "note": note,
                        "proxy": True, **quote})
    return out


def share_classes() -> list[dict]:
    """A/B spreads and where each sits against its own year.

    Reports the ratio and its z-score. Deliberately does not say what to do
    about it: a spread can sit two standard deviations from its mean for
    months, and whether closing it is worth anything depends on tax, holding
    period and whether the votes matter to the holder - none of which this
    program knows.
    """
    out = []
    for a_ticker, b_ticker, name in SHARE_CLASSES:
        a_data, b_data = _chart(a_ticker), _chart(b_ticker)
        if not a_data or not b_data:
            continue

        def closes(data):
            stamps = data.get("timestamp") or []
            values = data["indicators"]["quote"][0].get("close") or []
            return {s: v for s, v in zip(stamps, values) if v}

        a_closes, b_closes = closes(a_data), closes(b_data)
        shared = sorted(set(a_closes) & set(b_closes))
        if len(shared) < 60:
            continue

        ratios = [a_closes[s] / b_closes[s] for s in shared]
        mean = statistics.mean(ratios)
        deviation = statistics.pstdev(ratios)
        current = ratios[-1]
        # How unusual today is, in standard deviations. Zero means the spread
        # is exactly where it normally sits.
        z = (current - mean) / deviation if deviation else 0.0

        out.append({
            "name": name,
            "a": a_ticker,
            "b": b_ticker,
            "aPrice": round(a_closes[shared[-1]], 4),
            "bPrice": round(b_closes[shared[-1]], 4),
            "ratio": round(current, 4),
            "meanRatio": round(mean, 4),
            "sd": round(deviation, 4),
            "z": round(z, 2),
            "days": len(shared),
            # A spread whose whole range is narrower than the cost of trading
            # it is a curiosity, not an opportunity. Two standard deviations of
            # under 0.5% will not cover spread, fees and tax.
            "tradableRange": bool(deviation * 2 / mean > 0.005),
        })
    return out


def build() -> dict:
    print("context: commodities")
    metals = commodities()
    print("context: freight")
    rates = freight()
    print("context: share classes")
    classes = share_classes()
    return {
        "commodities": metals,
        "freight": rates,
        "shareClasses": classes,
        "_freightNote": (
            "The Baltic indices are a licensed product with no free feed. "
            "These are ETFs holding freight futures - they move with rates "
            "rather than with shipping equities, but carry roll cost and "
            "tracking error and can diverge from spot."
        ),
        "_shareClassNote": (
            "Ratio of the A price to the B price, with how far today sits from "
            "its own one-year mean. This is an observation, not a "
            "recommendation: a spread can stay unusual for months, and whether "
            "switching is worth anything depends on tax, holding period and "
            "whether the votes matter to you."
        ),
    }
