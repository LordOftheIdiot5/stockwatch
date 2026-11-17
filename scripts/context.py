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
import math
from datetime import datetime, timezone
import urllib.parse
import urllib.request
from daily_recovery import maybe_recover

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
    # Norwegian shipping, which the first pass missed entirely by only looking
    # at Swedish names. These carry the widest spreads on the list by some way.
    ("WWI.OL", "WWIB.OL", "Wilh. Wilhelmsen"),
    ("ODF.OL", "ODFB.OL", "Odfjell"),
    ("MAERSK-A.CO", "MAERSK-B.CO", "Maersk"),
    ("ATCO-A.ST", "ATCO-B.ST", "Atlas Copco"),
    ("SSAB-A.ST", "SSAB-B.ST", "SSAB"),
    ("ERIC-A.ST", "ERIC-B.ST", "Ericsson"),
    ("SKF-A.ST", "SKF-B.ST", "SKF"),
    ("HUSQ-A.ST", "HUSQ-B.ST", "Husqvarna"),
    ("SCA-A.ST", "SCA-B.ST", "SCA"),
    ("KINV-A.ST", "KINV-B.ST", "Kinnevik"),
    ("INVE-A.ST", "INVE-B.ST", "Investor"),
    ("VOLV-A.ST", "VOLV-B.ST", "Volvo"),
]

# OpenFIGI-discovered candidates. Provider symbols are proposed mappings, not
# independently confirmed FIGI-to-price identities. No automatic alert promotion.
AB_CANDIDATES = [
    ("ELUX-A.ST", "ELUX-B.ST", "Electrolux", "XSTO:ELECTROLUX AB", "SEK", "electrolux"),
    ("EPI-A.ST", "EPI-B.ST", "Epiroc", "XSTO:EPIROC AB", "SEK", "epiroc"),
    ("ESSITY-A.ST", "ESSITY-B.ST", "Essity", "XSTO:ESSITY AKTIEBOLAG", "SEK", "essity"),
    ("SAGA-A.ST", "SAGA-B.ST", "Sagax", "XSTO:SAGAX AB", "SEK", "sagax"),
    ("SVOL-A.ST", "SVOL-B.ST", "Svolder", "XSTO:SVOLDER AB", "SEK", "svolder"),
    ("ACRI-A.ST", "ACRI-B.ST", "Acrinova", "XSTO:ACRINOVA AB", "SEK", "acrinova"),
    ("ALBAV.HE", "ALBBV.HE", "Ålandsbanken", "XHEL:ALANDSBANKEN", "EUR", "landsbanken"),
    ("METSA.HE", "METSB.HE", "Metsä Board", "XHEL:METSA BOARD OYJ", "EUR", "mets"),
    ("ORNAV.HE", "ORNBV.HE", "Orion", "XHEL:ORION OYJ-CLASS", "EUR", "orion"),
]

def candidate_match(data, ticker, currency, name):
    meta = data.get("meta", {}) if isinstance(data, dict) else {}
    issuer = str(meta.get("longName") or meta.get("shortName") or "").casefold()
    return (meta.get("symbol") == ticker and meta.get("currency") == currency
            and meta.get("instrumentType") == "EQUITY" and name in issuer)

def rolling_summary(ratios, window):
    # Trading observations, not calendar days.
    if len(ratios) < window:
        return None
    values = ratios[-window:]
    mean = statistics.mean(values)
    sd = statistics.pstdev(values)
    return {"observations": window, "mean": round(mean, 6),
            "z": round((values[-1]-mean)/sd, 3) if sd else None}

# Both classes need real volume. A spread computed against a class that trades
# a few hundred shares a day is measuring stale quotes, not a price.
MIN_CLASS_VOLUME = 3000


def _chart(ticker: str, rng: str = "1y", interval: str = "1d") -> dict | None:
    url = f"{CHART}{urllib.parse.quote(ticker)}?range={rng}&interval={interval}"
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        payload = json.loads(urllib.request.urlopen(request, timeout=TIMEOUT).read())
    except Exception as error:                                   # noqa: BLE001
        print(f"  ! {ticker}: {error}")
        return None
    result = (payload.get("chart") or {}).get("result")
    if not result:return None
    def fetch_exact(url):
        req=urllib.request.Request(url,headers={"User-Agent":UA})
        with urllib.request.urlopen(req,timeout=TIMEOUT) as response:return response.read()
    return maybe_recover(result[0],ticker,fetch_exact) if interval=='1d' else result[0]


def _quote(ticker: str) -> dict | None:
    """Last price plus one-day and one-month change."""
    data = _chart(ticker)
    if not data:
        return None
    dated_closes=[(t,c) for t,c in zip(data.get("timestamp") or [], data["indicators"]["quote"][0].get("close") or []) if type(c) in (int,float) and math.isfinite(c) and c>0]
    closes=[c for _,c in dated_closes]
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
        "date": utc_day(dated_closes[-1][0]),
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
            out.append({"ticker": ticker, "name": name, "note": note,"unit":"USD",
                        "proxy": True, **quote})
    return out


def utc_day(stamp):
    return datetime.fromtimestamp(stamp, timezone.utc).date().isoformat() if stamp is not None else None

def valid_pair_closes(data):
    stamps = data.get("timestamp") or []
    quote = (data.get("indicators",{}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []
    latest = max(stamps, default=None)
    valid = {s: c for s, c, v in zip(stamps, closes, volumes)
             if type(c) in (int,float) and math.isfinite(c) and c > 0
             and type(v) in (int,float) and math.isfinite(v) and v > 0}
    return valid, latest

def latest_bar_health(data):
    """Status only; never substitute metadata price for a daily bar."""
    if not data:
        return {"status":"source_unavailable","reportedDate":None,"lastValidDate":None}
    valid, latest = valid_pair_closes(data)
    if latest is None:
        return {"status":"no_timestamp","reportedDate":None,"lastValidDate":None}
    quote = (data.get("indicators",{}).get("quote") or [{}])[0]
    stamps = data.get("timestamp") or []
    i = stamps.index(latest)
    def at(key):
        arr = quote.get(key) or []
        return arr[i] if i < len(arr) else None
    close, volume = at("close"), at("volume")
    if type(close) not in (int,float) or not math.isfinite(close) or close <= 0:
        reason = "missing_or_invalid_close"
    elif type(volume) not in (int,float) or not math.isfinite(volume) or volume < 0:
        reason = "missing_or_invalid_volume"
    elif volume == 0:
        reason = "zero_volume"
    else:
        reason = "valid_bar"
    return {"status":reason,"reportedDate":utc_day(latest),
            "lastValidDate":utc_day(max(valid,default=None))}

def share_classes(candidate_status=None, feed_health=None) -> list[dict]:
    """A/B spreads and where each sits against its own year.

    Reports the ratio and its z-score. Deliberately does not say what to do
    about it: a spread can sit two standard deviations from its mean for
    months, and whether closing it is worth anything depends on tax, holding
    period and whether the votes matter to the holder - none of which this
    program knows.
    """
    out = []
    entries = [(a,b,n,None,None,None) for a,b,n in SHARE_CLASSES] + AB_CANDIDATES
    for a_ticker, b_ticker, name, candidate_id, expected_currency, issuer in entries:
        status = {"id": candidate_id, "a": a_ticker, "b": b_ticker, "status": "source_unavailable"} if candidate_id else None
        if status is not None and candidate_status is not None:
            candidate_status.append(status)
        a_data, b_data = _chart(a_ticker), _chart(b_ticker)
        if feed_health is not None:
            feed_health.append({"name":name,"a":a_ticker,"b":b_ticker,"candidate":bool(candidate_id),"aHealth":latest_bar_health(a_data),"bHealth":latest_bar_health(b_data)})
        if not a_data or not b_data:
            continue
        if candidate_id and not (candidate_match(a_data,a_ticker,expected_currency,issuer) and candidate_match(b_data,b_ticker,expected_currency,issuer)):
            status["status"] = "metadata_mismatch"
            continue
        if status is not None:
            status["status"] = "currency_mismatch"

        currency = a_data.get("meta", {}).get("currency")
        if not currency or currency != b_data.get("meta", {}).get("currency"):
            continue
        a_closes, a_last = valid_pair_closes(a_data)
        b_closes, b_last = valid_pair_closes(b_data)
        shared = sorted(set(a_closes) & set(b_closes))
        if status is not None:
            status["status"] = "insufficient_aligned_observations"
            status["alignedObservations"] = len(shared)
        if len(shared) < 60:
            continue

        def volumes(data):
            return [v for v in (data["indicators"]["quote"][0].get("volume") or []) if v]

        a_volume = statistics.median(volumes(a_data) or [0])
        b_volume = statistics.median(volumes(b_data) or [0])
        if status is not None:
            status["status"] = "insufficient_volume"
        if min(a_volume, b_volume) < MIN_CLASS_VOLUME:
            continue

        ratios = [a_closes[s] / b_closes[s] for s in shared]
        mean = statistics.mean(ratios)
        deviation = statistics.pstdev(ratios)
        current = ratios[-1]
        # How unusual today is, in standard deviations. Zero means the spread
        # is exactly where it normally sits.
        z = (current - mean) / deviation if deviation else 0.0

        # A z-score assumes the spread oscillates around a stable level. Some
        # do not: Kinnevik's ratio walked from 1.04 to 1.30 and back to 1.11
        # over a year, so its "mean" is just the average of a drift and a
        # z-score of zero against it would read as "normal" when the series has
        # no normal. Comparing the two halves catches that - if the level has
        # moved by more than a standard deviation, the mean is not a level the
        # spread returns to and the z-score should not be read as one.
        midpoint = len(ratios) // 2
        first_half = statistics.mean(ratios[:midpoint])
        second_half = statistics.mean(ratios[midpoint:])
        drift = abs(second_half - first_half)
        stationary = bool(deviation and drift < deviation)

        if status is not None:
            status["status"] = "price_checks_passed_identity_review_required"
            status["priceDate"] = utc_day(shared[-1])
            # Do not publish new candidate price statistics until exact listing identities and usage rights are reviewed.
            continue
        out.append({
            "rolling": {str(n): rolling_summary(ratios,n) for n in (30,90,240)},
            "aMedianVolume": int(a_volume),
            "bMedianVolume": int(b_volume),
            "stationary": stationary,
            "stabilityMethod": "split_half_drift_heuristic",
            "priceDate": utc_day(shared[-1]),
            "aLatestDate": utc_day(a_last),
            "bLatestDate": utc_day(b_last),
            "latestPairEligible": shared[-1] == a_last == b_last,
            "currency": currency,
            "driftPct": round((second_half / first_half - 1) * 100, 2),
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
            "rangePct": round(deviation * 2 / mean * 100, 2),
        })
    # Widest spread first: that ordering answers the question someone opening
    # this panel is actually asking.
    out.sort(key=lambda r: -r["rangePct"])
    return out


def build() -> dict:
    print("context: commodities")
    metals = commodities()
    print("context: freight")
    rates = freight()
    print("context: share classes")
    candidates = []
    feed_health = []
    classes = share_classes(candidates,feed_health)
    return {
        "commodities": metals,
        "freight": rates,
        "shareClasses": classes,
        "shareClassCandidateChecks": candidates,
        "shareClassFeedHealth": feed_health,
        "_freightNote": (
            "The Baltic indices are a licensed product with no free feed. "
            "These are ETFs holding freight futures - they move with rates "
            "rather than with shipping equities, but carry roll cost and "
            "tracking error and can diverge from spot."
        ),
        "_shareClassNote": (
            "Ratio of the A price to the B price, with how far today sits from "
            "its own one-year mean. Pairs marked drifting have no stable mean "
            "to revert to - their level has moved over the year, so the "
            "standard-deviation figure describes the drift rather than an "
            "opportunity. This is an observation, not a recommendation: a "
            "spread can stay unusual for months, and whether switching is worth "
            "anything depends on tax, holding period and whether the votes "
            "matter to you."
        ),
    }
