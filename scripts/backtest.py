"""Ask whether the price and volume thresholds detect anything.

Everything in scan.py has been a guess so far, and the page says so. This is the
measurement: rebuild what the scanner would have flagged on every day of the
past two years, and compare what happened next against what happened on all the
other days.

What is being asked is narrow, and worth stating precisely. Not "is this
profitable" - that depends on costs, slippage, sizing and a dozen things not
modelled here. The question is whether a flagged day is followed by different
behaviour from an ordinary day. If it is not, the thresholds are decoration.

Three decisions that decide whether the answer means anything:

  entry at the next close    The signal needs the full day's volume, so it is
                             only complete once the day is over. Measuring from
                             the close you just observed assumes you traded on
                             information you did not have until it had passed.
                             That single choice flatters results more than any
                             threshold does.

  a baseline of every other  A signal that returns 4% is worthless if every day
  day in the same universe   returns 4%. The comparison is against the same
                             names over the same period, not against zero.

  bootstrap by date          Returns on one day are not independent across a
                             hundred European industrials - they share a market.
                             Treating 40,000 stock-days as 40,000 independent
                             observations would make almost anything look
                             significant. Resampling whole dates keeps that
                             correlation intact.

Run: python scripts/backtest.py [years]
"""
from __future__ import annotations

import json
import random
import statistics
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sources                                                    # noqa: E402
from scan import BASELINE_DAYS, MOVE_SIGMA, RVOL_ALERT            # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
HORIZONS = (1, 5, 20)
BOOTSTRAP = 2000


def bars_for(entry: dict, rng: str) -> tuple[str, dict, list]:
    data = sources.chart(entry["ticker"], rng=rng)
    return entry["ticker"], entry, (data["bars"] if data else [])


def build(years: int) -> tuple[dict, dict]:
    watchlist = json.loads((ROOT / "watchlist.json").read_text(encoding="utf-8"))["tickers"]
    print(f"Fetching {years}y of daily bars for {len(watchlist)} companies")
    series: dict[str, list] = {}
    meta: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=10) as pool:
        for ticker, entry, bars in pool.map(lambda e: bars_for(e, f"{years}y"), watchlist):
            if len(bars) > BASELINE_DAYS + max(HORIZONS) + 5:
                series[ticker] = bars
                meta[ticker] = entry
    print(f"  {len(series)} usable series, "
          f"{sum(len(b) for b in series.values()):,} stock-days\n")
    return series, meta


def measure(series: dict, meta: dict) -> list[dict]:
    """Every (stock, day) with the scanner's numbers and what happened next.

    The market baseline is the same one scan.py uses: the median move of the
    watchlist itself on that day, so a stock is only "up" if it outran the rest
    of the list.
    """
    # Index by date so the day's market move can be computed across names.
    by_date: dict[str, dict[str, float]] = defaultdict(dict)
    for ticker, bars in series.items():
        for previous, current in zip(bars, bars[1:]):
            if previous["close"]:
                by_date[current["date"]][ticker] = (
                    current["close"] - previous["close"]) / previous["close"]
    market = {d: statistics.median(v.values()) for d, v in by_date.items() if v}

    rows = []
    for ticker, bars in series.items():
        thin = bool(meta[ticker].get("thin"))
        for i in range(BASELINE_DAYS + 1, len(bars) - max(HORIZONS) - 1):
            window = bars[i - BASELINE_DAYS:i]
            latest, previous = bars[i], bars[i - 1]
            if not previous["close"] or not latest["close"]:
                continue

            volumes = [b["volume"] for b in window if b["volume"]]
            median_volume = statistics.median(volumes) if volumes else 0
            rvol = latest["volume"] / median_volume if median_volume else 0

            returns = [(b["close"] - a["close"]) / a["close"]
                       for a, b in zip(window, window[1:]) if a["close"]]
            sigma = statistics.pstdev(returns) if len(returns) > 2 else 0
            if not sigma:
                continue
            change = (latest["close"] - previous["close"]) / previous["close"]
            excess = change - market.get(latest["date"], 0.0)

            # Entry is the NEXT close: the signal is not complete until the day
            # it describes has finished.
            entry_close = bars[i + 1]["close"]
            if not entry_close:
                continue
            forward = {}
            for h in HORIZONS:
                exit_bar = bars[i + 1 + h]
                if exit_bar["close"]:
                    forward[h] = (exit_bar["close"] - entry_close) / entry_close

            rows.append({
                "ticker": ticker, "date": latest["date"], "thin": thin,
                "rvol": rvol, "excessSigma": excess / sigma,
                "excess": excess, "forward": forward,
            })
    return rows


def stats(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    return {
        "n": len(values),
        "mean": statistics.mean(values) * 100,
        "median": statistics.median(values) * 100,
        "up": sum(1 for v in values if v > 0) / len(values) * 100,
    }


def bootstrap_gap(flagged: list[tuple[str, float]], base: list[tuple[str, float]],
                  rounds: int = BOOTSTRAP) -> tuple[float, float]:
    """Confidence interval for the difference in mean, resampling whole dates.

    Stock-days are not independent: a hundred European names on one day share
    the same market. Resampling dates rather than rows keeps that correlation,
    and the interval it gives is several times wider than a naive one - which
    is the honest width.

    Only a sum and a count per date are needed, because the mean of several
    days pooled is their summed values over their summed counts. Carrying the
    values themselves meant rebuilding a forty-thousand element list two
    thousand times per test, which does not finish.
    """
    def fold(rows):
        sums, counts = defaultdict(float), defaultdict(int)
        for d, v in rows:
            sums[d] += v
            counts[d] += 1
        return sums, counts

    f_sum, f_n = fold(flagged)
    b_sum, b_n = fold(base)
    dates = sorted(set(f_sum) | set(b_sum))
    if not dates or not flagged:
        return (0.0, 0.0)

    rng = random.Random(20260825)
    size = len(dates)
    gaps = []
    for _ in range(rounds):
        fs = fn = bs = bn = 0.0
        for _ in range(size):
            d = dates[rng.randrange(size)]
            fs += f_sum.get(d, 0.0)
            fn += f_n.get(d, 0)
            bs += b_sum.get(d, 0.0)
            bn += b_n.get(d, 0)
        if fn and bn:
            gaps.append((fs / fn - bs / bn) * 100)
    if not gaps:
        return (0.0, 0.0)
    gaps.sort()
    return (gaps[int(0.025 * len(gaps))], gaps[int(0.975 * len(gaps))])


def report(rows: list[dict], name: str, hit, horizon: int) -> dict | None:
    flagged = [(r["date"], r["forward"][horizon]) for r in rows
               if horizon in r["forward"] and hit(r)]
    base = [(r["date"], r["forward"][horizon]) for r in rows
            if horizon in r["forward"] and not hit(r)]
    if len(flagged) < 30:
        print(f"  {name:<34} {len(flagged):>5} signals - too few to say anything")
        return None
    f_stats, b_stats = stats([v for _, v in flagged]), stats([v for _, v in base])
    lo, hi = bootstrap_gap(flagged, base)
    gap = f_stats["mean"] - b_stats["mean"]
    verdict = "nothing" if lo <= 0 <= hi else ("higher" if lo > 0 else "lower")
    print(f"  {name:<34} {f_stats['n']:>5}  "
          f"{f_stats['mean']:>+7.3f}%  vs {b_stats['mean']:>+7.3f}%  "
          f"gap {gap:>+7.3f}%  95% CI [{lo:>+6.2f}, {hi:>+6.2f}]  {verdict}")
    return {"signal": name, "horizon": horizon, "n": f_stats["n"],
            "mean": f_stats["mean"], "baseMean": b_stats["mean"],
            "gap": gap, "ci": [lo, hi], "verdict": verdict,
            "upRate": f_stats["up"], "baseUpRate": b_stats["up"]}


def main() -> int:
    years = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    series, meta = build(years)
    rows = measure(series, meta)
    dates = {r["date"] for r in rows}
    print(f"Measured {len(rows):,} stock-days across {len(dates)} trading days")
    print(f"Thresholds as configured: RVOL >= {RVOL_ALERT}, "
          f"|excess sigma| >= {MOVE_SIGMA}\n")

    tests = [
        ("volume >= 2.5x median", lambda r: r["rvol"] >= RVOL_ALERT and not r["thin"]),
        ("volume >= 2.5x, thin included", lambda r: r["rvol"] >= RVOL_ALERT),
        ("up >= 2 sigma vs market", lambda r: r["excessSigma"] >= MOVE_SIGMA),
        ("down <= -2 sigma vs market", lambda r: r["excessSigma"] <= -MOVE_SIGMA),
        ("either direction >= 2 sigma", lambda r: abs(r["excessSigma"]) >= MOVE_SIGMA),
        ("volume AND up 2 sigma", lambda r: r["rvol"] >= RVOL_ALERT
         and r["excessSigma"] >= MOVE_SIGMA),
        ("volume AND down 2 sigma", lambda r: r["rvol"] >= RVOL_ALERT
         and r["excessSigma"] <= -MOVE_SIGMA),
        ("anything the scanner alerts on",
         lambda r: (r["rvol"] >= RVOL_ALERT and not r["thin"])
         or abs(r["excessSigma"]) >= MOVE_SIGMA),
    ]

    # --- controls -------------------------------------------------------
    # Two questions have to be answered before any number above means
    # anything: can this harness find an effect that is really there, and does
    # it invent ones that are not?
    print("--- controls ---")
    rng = random.Random(20260826)
    for r in rows:
        r["_coin"] = rng.random()

    # Negative control. A signal with no information, flagging the same share
    # of days as the real ones. Whatever it "finds" is the noise floor.
    share = sum(1 for r in rows if r["rvol"] >= RVOL_ALERT) / max(len(rows), 1)
    placebo_hits = 0
    for horizon in HORIZONS:
        got = report(rows, f"placebo: a coin flip ({share:.1%} of days)",
                     lambda r: r["_coin"] < share, horizon)
        if got and got["verdict"] != "nothing":
            placebo_hits += 1

    # Positive control. A signal that peeks at the answer. If this does not
    # show up enormous and unambiguous, the measurement is broken and every
    # other line is meaningless.
    for horizon in HORIZONS:
        report(rows, "positive control: peeks at the future",
               lambda r, h=horizon: r["forward"].get(h, 0) > 0, horizon)
    print()

    results = []
    for horizon in HORIZONS:
        print(f"--- {horizon} trading day{'s' if horizon > 1 else ''} after entry "
              f"(entry at the next close) ---")
        print(f"  {'signal':<34} {'n':>5}  {'flagged':>8}  {'baseline':>10}"
              f"  {'gap':>12}  {'95% CI':>22}")
        for name, hit in tests:
            got = report(rows, name, hit, horizon)
            if got:
                results.append(got)
        print()

    out = ROOT / "data" / "backtest.json"
    out.write_text(json.dumps({
        "years": years, "stockDays": len(rows), "tradingDays": len(dates),
        "entry": "next close after the signal day",
        "thresholds": {"rvol": RVOL_ALERT, "sigma": MOVE_SIGMA},
        "results": results,
    }, indent=1), encoding="utf-8")

    worked = [r for r in results if r["verdict"] != "nothing"]
    expected = len(results) * 0.05
    print(f"{len(worked)} of {len(results)} signal/horizon pairs differ from "
          f"baseline at 95% confidence.")
    print(f"Chance alone would produce about {expected:.1f} at this many tests, "
          f"and the coin flip produced {placebo_hits}.")
    if worked:
        print("Nominally surviving:")
        for r in sorted(worked, key=lambda x: -abs(x["gap"])):
            print(f"  {r['signal']} at {r['horizon']}d: {r['gap']:+.3f}% "
                  f"95% CI [{r['ci'][0]:+.2f}, {r['ci'][1]:+.2f}]")
    # A threshold that only clears the bar because the bar was tried 24 times
    # has not cleared it. Bonferroni is crude and it is the right kind of crude
    # here: it asks what would survive if only one test had been run.
    strict = [r for r in results if r["ci"][0] > 0 or r["ci"][1] < 0]
    tight = [r for r in strict if abs(r["gap"]) > abs(r["ci"][1] - r["ci"][0]) / 2]
    print()
    print(f"Surviving a correction for having run {len(results)} tests: "
          f"{len(tight)}")

    # --- does anything that survived survive being split in half? --------
    # The strongest cheap test there is. A real effect is present in both
    # halves of the period; one that only exists in the half where it was
    # found is the search itself showing through.
    if worked:
        print("--- the same signals, measured on each half of the period ---")
        ordered = sorted({r["date"] for r in rows})
        midpoint = ordered[len(ordered) // 2]
        first = [r for r in rows if r["date"] < midpoint]
        second = [r for r in rows if r["date"] >= midpoint]
        lookup = dict(tests)
        for survivor in worked:
            hit = lookup[survivor["signal"]]
            print(f"  {survivor['signal']} at {survivor['horizon']}d "
                  f"(whole period {survivor['gap']:+.3f}%)")
            for label, half in (("first half ", first), ("second half", second)):
                report(half, f"    {label} to {midpoint if label.startswith('first') else ordered[-1]}",
                       hit, survivor["horizon"])
        print()

    print(f"\nwrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
