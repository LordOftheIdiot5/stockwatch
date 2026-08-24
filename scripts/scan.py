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
    for item in disclosures:
        symbol = (item.get("issuer") or "").upper() or ticker_from_title(item["title"])
        if not symbol or symbol not in symbols:
            continue
        if is_routine(item["title"]):
            continue
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
        mark = "REG" if a.get("regulatory") else "   "
        print(f"  [{mark}] {a['ticker']:<12} {a['headline'][:70]}")

    # Hand the fresh ones to the workflow so it can decide whether to shout.
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
            fh.write(f"fresh={len(fresh)}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
