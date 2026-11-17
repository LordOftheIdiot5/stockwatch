"""Private US issuer directory and bounded SEC XBRL batch enrichment.
No market prices, no inferred MICs, and no publication or scheduling.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import time
from pathlib import Path
from datetime import datetime, timezone
from free_research import fetch, sec_facts, SEC, ROOT

DIRECTORY = "https://www.sec.gov/files/company_tickers_exchange.json"
TERMS = "https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data"

def normalize_directory(data):
    fields = data["fields"]
    expected = {"cik", "name", "ticker", "exchange"}
    if len(fields) != 4 or set(fields) != expected:
        raise ValueError("unknown SEC directory schema")
    rows = {}
    for entry in data["data"]:
        if len(entry) != len(fields):
            raise ValueError("malformed SEC directory row")
        r = dict(zip(fields, entry))
        cik, name, ticker, exchange = (r[k] for k in ("cik", "name", "ticker", "exchange"))
        if type(cik) is not int or not 0 < cik < 10**10:
            raise ValueError("invalid CIK")
        if not isinstance(name, str) or not name.strip() or not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("missing issuer or ticker")
        if exchange is not None and not isinstance(exchange, str):
            raise ValueError("invalid exchange")
        record = {"cik": str(cik).zfill(10), "issuer": name.strip(),
                  "symbol": ticker.strip(), "reportedExchange": exchange,
                  "identityStatus": "sec_reported_candidate", "priceAvailable": False}
        key = (record["cik"], record["symbol"], exchange)
        if key in rows and rows[key] != record:
            raise ValueError("conflicting directory records")
        rows[key] = record
    if not rows:
        raise ValueError("empty SEC directory")
    return sorted(rows.values(), key=lambda r: (r["cik"], r["symbol"], r["reportedExchange"] or ""))

def collect(get, agent, symbols=(), limit=25, delay=0.5, sleep=time.sleep):
    if not re.search(r"[^@\s]+@[^@\s]+\.[^@\s]+", agent):
        raise ValueError("declared SEC organization and contact required")
    if type(limit) is not int or not 1 <= limit <= 100 or delay < 0.5:
        raise ValueError("batch limits")
    listings = normalize_directory(get(DIRECTORY, agent))
    wanted = {s.upper() for s in symbols}
    matches = [r for r in listings if r["symbol"].upper() in wanted]
    missing = sorted(wanted - {r["symbol"].upper() for r in matches})
    if missing:
        raise ValueError("unmatched SEC symbols: " + ", ".join(missing))
    ciks = sorted({r["cik"] for r in matches})
    if len(ciks) > limit:
        raise ValueError("selected issuers exceed batch cap")
    results, failures = [], []
    for cik in ciks:
        sleep(delay)
        u = SEC + cik + ".json"
        try:
            facts = sec_facts(get(u, agent), cik)
            results.append({"sourceUrl": u, **facts})
        except Exception as exc:
            failures.append({"cik": cik, "status": "unavailable", "errorType": type(exc).__name__})
            # Stop on the first transport/schema failure rather than repeatedly calling a blocked service.
            break
    return {"schemaVersion": 1, "retrievedAt": datetime.now(timezone.utc).isoformat(),
            "source": DIRECTORY, "accessPolicy": TERMS, "scope": "SEC reported ticker candidates, not verified exchange listings",
            "listings": listings, "selectedIssuerCount": len(ciks), "issuerFacts": results,
            "failures": failures, "unattemptedIssuerCount": len(ciks)-len(results)-len(failures),
            "pricePublicationAllowed": False, "publicExportEnabled": False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbol", action="append", default=[])
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    out = a.output.expanduser().resolve()
    if out == ROOT or ROOT in out.parents:
        raise ValueError("output must be outside repository")
    result = collect(fetch, os.getenv("STOCKWATCH_SEC_USER_AGENT", "").strip(), a.symbol, a.limit)
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    tmp.replace(out)
    print(json.dumps({"directoryListings": len(result["listings"]), "issuersEnriched": len(result["issuerFacts"]),
                      "failures": len(result["failures"]), "unattempted": result["unattemptedIssuerCount"],
                      "pricePublicationAllowed": False}))
    return 1 if result["failures"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
