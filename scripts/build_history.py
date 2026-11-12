"""Build source-backed historical OHLCV caches for Stockwatch company charts.

Run from the repository root:
  python scripts/build_history.py --limit 20
  python scripts/build_history.py --full --refresh-days 7

This is an OPTIONAL enrichment job, separate from the time-sensitive scanner.
It uses the repo's existing scripts/sources.py Yahoo chart client, with a
conservative delay. Yahoo is an unofficial endpoint; check usage/redistribution
rights before commercializing, and use a licensed provider if necessary.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

OUT = ROOT / "data" / "history"


def validate_bars(bars: list[dict]) -> list[dict]:
    clean, seen = [], set()
    for row in bars:
        d = row.get("date")
        c = row.get("close")
        if not isinstance(d, str) or len(d) != 10 or d in seen:
            continue
        try:
            date.fromisoformat(d)
        except ValueError:
            continue
        if not isinstance(c, (int, float)) or not math.isfinite(c) or c <= 0:
            continue
        seen.add(d)
        vol = row.get("volume")
        clean.append({"date": d, "close": round(c, 6),
                      "volume": int(vol) if isinstance(vol, (int, float)) and vol >= 0 else None})
    return sorted(clean, key=lambda x: x["date"])


def needs_update(path: Path, refresh_days: int, now: datetime) -> bool:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        then = datetime.fromisoformat(obj["updated"])
        return (now - then).total_seconds() >= refresh_days * 86400
    except (OSError, ValueError, TypeError, KeyError):
        return True


def main() -> int:
    from sources import chart  # noqa: E402  # Existing scanner source module
    a = argparse.ArgumentParser()
    a.add_argument("--limit", type=int, default=20, help="max symbols to fetch this run")
    a.add_argument("--full", action="store_true", help="fetch all due symbols")
    a.add_argument("--refresh-days", type=int, default=7)
    a.add_argument("--delay", type=float, default=1.2)
    args = a.parse_args()
    if args.limit < 1 or args.delay < 0 or args.refresh_days < 1:
        a.error("limit, refresh-days, delay must be nonnegative; limit and refresh-days >= 1")
    watchlist = json.loads((ROOT / "watchlist.json").read_text(encoding="utf-8"))["tickers"]
    OUT.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    due = [e for e in watchlist if needs_update(OUT / (e["ticker"] + ".json"), args.refresh_days, now)]
    count = len(due) if args.full else min(len(due), args.limit)
    good = 0
    print(f"History files due: {len(due)}; fetching at most {count}. Nothing invented on failure.")
    for i, entry in enumerate(due[:count]):
        ticker = entry["ticker"]
        response = chart(ticker, rng="5y", interval="1d")
        bars = validate_bars((response or {}).get("bars") or [])
        if len(bars) < 21:
            print(f"SKIP {ticker}: only {len(bars)} valid trading days")
        else:
            payload = {"ticker": ticker, "source": "Yahoo chart / daily closes (unadjusted)",
                       "updated": now.isoformat(timespec="seconds"), "bars": bars}
            path = OUT / (ticker + ".json")
            tmp = path.with_suffix('.tmp')
            tmp.write_text(json.dumps(payload, separators=(',', ':')), encoding="utf-8")
            tmp.replace(path)
            good += 1
            print(f"OK   {ticker}: {len(bars)} trading days")
        if i < count-1:
            time.sleep(args.delay)
    print(f"Updated {good}/{count} files; no chart is shown for absent historical data.")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
