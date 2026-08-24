"""Pick watchlist candidates on measurable properties, not opinion.

This does not try to guess which shares will rise - nobody can do that, and a
scanner does not need it. It selects for instruments where the scanner has
something to detect:

  liquidity   enough daily volume that a volume spike means participation
              rather than one order
  movement    enough realised volatility that a 2-sigma day happens sometimes
  spread      more than one exchange, so the multi-market handling is exercised

An illiquid, becalmed share produces no signal and teaches the tool nothing.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import sources                                                   # noqa: E402

# Candidate pool: liquid European names across several exchanges and sectors.
POOL = [
    ("EQNR.OL", "Equinor"), ("NHY.OL", "Norsk Hydro"), ("YAR.OL", "Yara"),
    ("AKRBP.OL", "Aker BP"), ("FRO.OL", "Frontline"), ("MOWI.OL", "Mowi"),
    ("SALM.OL", "SalMar"), ("KOG.OL", "Kongsberg Gruppen"), ("NAS.OL", "Norwegian Air"),
    ("REC.OL", "REC Silicon"), ("AKSO.OL", "Aker Solutions"), ("SUBC.OL", "Subsea 7"),
    ("TEL.OL", "Telenor"), ("DNB.OL", "DNB Bank"), ("ORK.OL", "Orkla"),
    ("VOLV-B.ST", "Volvo B"), ("ERIC-B.ST", "Ericsson B"), ("SAND.ST", "Sandvik"),
    ("EVO.ST", "Evolution"), ("SINCH.ST", "Sinch"), ("EMBRAC-B.ST", "Embracer"),
    ("VWS.CO", "Vestas Wind"), ("NOVO-B.CO", "Novo Nordisk"), ("MAERSK-B.CO", "Maersk B"),
    ("NOKIA.HE", "Nokia"), ("FORTUM.HE", "Fortum"),
    ("SAP.DE", "SAP"), ("IFX.DE", "Infineon"), ("RHM.DE", "Rheinmetall"),
    ("AIR.PA", "Airbus"), ("ASML.AS", "ASML"),
]

MIN_MEDIAN_VOLUME = 200_000        # shares/day; below this a spike is one order
MIN_BARS = 40


def profile(ticker: str, name: str) -> dict | None:
    data = sources.chart(ticker, rng="6mo")
    if not data or len(data["bars"]) < MIN_BARS:
        return None
    bars = data["bars"]

    volumes = [b["volume"] for b in bars if b["volume"]]
    if not volumes:
        return None
    median_volume = statistics.median(volumes)

    returns = []
    for a, b in zip(bars, bars[1:]):
        if a["close"]:
            returns.append((b["close"] - a["close"]) / a["close"])
    if len(returns) < 20:
        return None
    daily_sigma = statistics.pstdev(returns)
    annual_vol = daily_sigma * (252 ** 0.5) * 100

    # How often a 2-sigma day actually happened. A share that never moves gives
    # the scanner nothing to find, however large it is.
    big_days = sum(1 for r in returns if abs(r) > 2 * daily_sigma)

    return {
        "ticker": data["ticker"],
        "name": name,
        "exchange": data["exchange"],
        "currency": data["currency"],
        "medianVolume": int(median_volume),
        "annualVolPct": round(annual_vol, 1),
        "twoSigmaDays": big_days,
        "bars": len(bars),
    }


def main() -> int:
    print(f"Profiling {len(POOL)} candidates over 6 months\n")
    rows = []
    for ticker, name in POOL:
        p = profile(ticker, name)
        if not p:
            print(f"  skip {ticker}: no usable data")
            continue
        rows.append(p)
        print(f"  {p['ticker']:<13} {p['annualVolPct']:>5}% vol  "
              f"{p['medianVolume']:>10,} med vol  {p['twoSigmaDays']:>2} big days")

    liquid = [r for r in rows if r["medianVolume"] >= MIN_MEDIAN_VOLUME]
    print(f"\n{len(liquid)} of {len(rows)} clear the liquidity floor "
          f"({MIN_MEDIAN_VOLUME:,} shares/day)")

    # Rank by how much there is to detect, then spread across exchanges so no
    # single market dominates the list.
    liquid.sort(key=lambda r: (-r["twoSigmaDays"], -r["annualVolPct"]))
    chosen, per_exchange = [], {}
    for row in liquid:
        market = row["exchange"]
        if per_exchange.get(market, 0) >= 4:
            continue
        per_exchange[market] = per_exchange.get(market, 0) + 1
        chosen.append(row)
        if len(chosen) == 10:
            break

    print("\nSelected:")
    for r in chosen:
        print(f"  {r['ticker']:<13} {r['name']:<20} {r['exchange']:<12} "
              f"vol {r['annualVolPct']}%  {r['twoSigmaDays']} big days")

    out = Path(__file__).resolve().parent.parent / "watchlist.json"
    out.write_text(json.dumps({
        "_comment": "Chosen by scripts/select.py on liquidity, realised volatility "
                    "and how often a 2-sigma day occurred. Not a view on direction.",
        "tickers": [
            {"ticker": r["ticker"], "name": r["name"], "exchange": r["exchange"],
             "annualVolPct": r["annualVolPct"], "medianVolume": r["medianVolume"]}
            for r in chosen
        ],
    }, indent=2), encoding="utf-8")
    print(f"\nwrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
