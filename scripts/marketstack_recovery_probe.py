"""Marketstack V2 private exact-session recovery probe. No quote publication."""
import argparse
import json
import math
import os
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://api.marketstack.com/v2/eod"
MARKETS = {
    "OL": ("XOSL", "NOK"), "ST": ("XSTO", "SEK"), "CO": ("XCSE", "DKK"),
    "DE": ("XETR", "EUR"), "PA": ("XPAR", "EUR"), "MI": ("XMIL", "EUR"),
    "BR": ("XBRU", "EUR"), "VI": ("XWBO", "EUR"), "MC": ("XMAD", "EUR"),
    "HE": ("XHEL", "EUR"), "AS": ("XAMS", "EUR"), "IR": ("XMSM", "EUR"),
    "HK": ("XHKG", "HKD"),
}
SAMPLE = ("SALM.OL", "ANDF.OL", "WWI.OL", "INVE-B.ST", "VOLV-B.ST",
          "NOVO-B.CO", "SIE.DE", "AIR.PA", "UCG.MI", "ASML.AS",
          "CAF.MC", "VIG.VI", "ELI.BR", "KCR.HE", "GVR.IR", "1913.HK",
          "KLDVK.OL", "NOBA.ST", "TKMS.DE", "CADLR.OL")
MISSING = frozenset("KLDVK.OL PLCAN.OL SBNOR.OL BOHUS.OL CMBTO.OL AVARDA.ST MORROW.ST NOBA.ST ELLOS.ST BLUE.ST QBEN.ST PFSE.DE 1AST.DE TKMS.DE OBCK.DE".split())

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def fetch(symbol, mic, day, key):
    query = urlencode({"access_key": key, "symbols": symbol, "exchange": mic,
                       "date_from": day, "date_to": day, "limit": 10})
    req = Request(BASE + "?" + query, headers={"Accept": "application/json",
                  "User-Agent": "StockwatchResearch/1.0"})
    with build_opener(NoRedirect()).open(req, timeout=25) as response:
        raw = response.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError("response_limit")
    return json.loads(raw)

def validate(payload, symbol, mic, currency, day):
    if not isinstance(payload, dict):
        return "unknown_schema"
    if "error" in payload:
        return "provider_error"
    rows = payload.get("data")
    if not isinstance(rows, list):
        return "unknown_schema"
    if not rows:
        return "no_data"
    if len(rows) != 1:
        return "ambiguous_response"
    r = rows[0]
    if not isinstance(r, dict):
        return "unknown_schema"
    if r.get("symbol") != symbol or (r.get("exchange_code") or r.get("exchange")) != mic:
        return "identity_mismatch"
    if r.get("price_currency") != currency:
        return "currency_unverified_or_mismatch"
    try:
        stamp = datetime.fromisoformat(r["date"].replace("Z", "+00:00"))
        if stamp.tzinfo is None or stamp.date().isoformat() != day:
            return "session_mismatch"
    except (KeyError, TypeError, ValueError, AttributeError):
        return "invalid_date"
    values = [r.get(k) for k in ("open", "high", "low", "close", "volume")]
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        return "invalid_ohlcv"
    o, h, l, c, v = values
    if not 0 < l <= min(o, c) <= max(o, c) <= h or v < 0:
        return "invalid_ohlcv"
    return "zero_volume_review" if v == 0 else "exact_session_bar"

def probe(symbols, day, key, get=fetch, pause=time.sleep):
    rows = []
    for symbol in symbols:
        mic, currency = MARKETS[symbol.rsplit(".", 1)[1]]
        try:
            status = validate(get(symbol, mic, day, key), symbol, mic, currency, day)
        except HTTPError as e:
            status = "http_" + str(e.code)
        except Exception:
            # Never print exception strings or URLs containing the API key.
            status = "transport_or_parse_error"
        row = {"ticker": symbol, "mic": mic, "session": day,
               "catalogueMatch": symbol not in MISSING, "status": status,
               "pricePublicationAllowed": False}
        rows.append(row)
        print(json.dumps(row), flush=True)
        if status in ("http_401", "http_403", "http_429", "provider_error",
                      "transport_or_parse_error", "unknown_schema"):
            break
        pause(1)
    return rows

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--date", required=True)
    p.add_argument("--budget", type=int, default=20)
    p.add_argument("--mode", choices=("sample", "missing", "catalogue"), default="sample")
    p.add_argument("--authorized-test", action="store_true")
    p.add_argument("--symbol", action="append")
    a = p.parse_args()
    if not a.authorized_test:
        p.error("confirm your provider plan permits this private evaluation")
    if date.fromisoformat(a.date).isoformat() != a.date or a.date >= date.today().isoformat():
        p.error("use a completed calendar date")
    if not 1 <= a.budget <= 100:
        p.error("budget must be 1-100; check remaining monthly allowance")
    key = os.environ.get("STOCKWATCH_MARKETSTACK_API_KEY", "").strip()
    if not key:
        p.error("missing STOCKWATCH_MARKETSTACK_API_KEY")
    watch = [r["ticker"] for r in json.loads((ROOT / "watchlist.json").read_text())["tickers"]]
    candidates = list(SAMPLE) if a.mode == "sample" else [
        s for s in watch if (s in MISSING) == (a.mode == "missing")]
    symbols = list(dict.fromkeys(a.symbol or candidates))
    if not set(symbols) <= set(watch):
        p.error("only monitored watchlist symbols are allowed")
    if a.symbol and len(symbols) > a.budget:
        p.error("explicit selection exceeds request budget")
    try:
        auth = fetch("AAPL", "XNAS", a.date, key)
        auth_status = "provider_error" if isinstance(auth, dict) and "error" in auth else "response_ok" if isinstance(auth, dict) and isinstance(auth.get("data"), list) else "unexpected_schema"
    except HTTPError as e:
        auth_status = "http_" + str(e.code)
    except Exception:
        auth_status = "transport_or_parse_error"
    print(json.dumps({"authenticationControl":"AAPL", "status":auth_status}), flush=True)
    if auth_status != "response_ok":
        return 1
    rows = probe(symbols[:max(0, a.budget-1)], a.date, key)
    print(json.dumps({"requested": min(len(symbols), a.budget-1), "attempted": len(rows),
                      "exactSessionBars": sum(r["status"] == "exact_session_bar" for r in rows),
                      "publicationEnabled": False, "pricesStored": False}))
    return 0 if any(r["status"] == "exact_session_bar" for r in rows) else 1

if __name__ == "__main__":
    raise SystemExit(main())
