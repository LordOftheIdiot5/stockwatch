"""N09a: inspect a manually downloaded Nasdaq regulatory CSV privately.

Optional one-file download follows a currently advertised official report link.
No archive, quote normalization, row export or publication. Header
aliases are candidate regulatory field names, not a verified Nasdaq schema.
"""
import argparse
import csv
import io
import json
from pathlib import Path
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from delayed_exchange import NAS_PORTALS, nasdaq_links

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 100_000
FIELDS = {
    "tradingdatetime": "trade_time", "tradedatetime": "trade_time",
    "publicationdatetime": "publication_time", "publicationtime": "publication_time",
    "mifidinstrumentid": "instrument_id", "instrumentidentificationcode": "instrument_id",
    "isin": "instrument_id", "mifidprice": "price", "price": "price",
    "mifidquantity": "quantity", "quantity": "quantity",
    "mifidcurrency": "currency", "pricecurrency": "currency", "currency": "currency",
    "venue": "venue", "venueofexecution": "venue", "mic": "venue",
    "tradeuniqueidentifier": "trade_id", "transactionidentificationcode": "trade_id",
    "flags": "flags", "tradeflags": "flags",
}
REQUIRED = {"trade_time", "instrument_id", "price", "quantity", "venue"}


def key(value):
    return "".join(c for c in value.casefold() if c.isascii() and c.isalnum())


def inspect_csv(raw):
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("Empty or oversized CSV")
    text = raw.decode("utf-8-sig", errors="strict")
    if "\x00" in text:
        raise ValueError("Unexpected binary content")
    matches = []
    for sep in (",", ";", "\t"):
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=sep, strict=True)
        try:
            for _ in range(4):
                header = next(reader, None)
                if header is None:
                    break
                normalized = [key(v) for v in header]
                roles = [FIELDS.get(v) for v in normalized]
                known = [v for v in roles if v]
                if REQUIRED.issubset(known):
                    if len(set(normalized)) != len(normalized) or len(set(known)) != len(known):
                        raise ValueError("Ambiguous header")
                    count = malformed = 0
                    for row in reader:
                        if not row:
                            continue
                        count += 1
                        if count > MAX_ROWS:
                            raise ValueError("Row limit exceeded")
                        if len(row) != len(header):
                            malformed += 1
                    matches.append({"delimiter": {",": "comma", ";": "semicolon", "\t": "tab"}[sep],
                                    "column_count": len(header), "candidate_field_roles": sorted(known),
                                    "unrecognized_column_count": len(header)-len(known),
                                    "row_count": count, "malformed_row_count": malformed})
                    break
        except csv.Error as exc:
            raise ValueError("Malformed CSV") from exc
    if len(matches) != 1:
        raise ValueError("No unique candidate regulatory header")
    return {"status": "candidate_header_observed", **matches[0],
            "provider_schema_verified": False, "quote_normalization_enabled": False,
            "retention_enabled": False, "public_publication": False}


def inspect_file(path):
    path = Path(path).expanduser().resolve()
    if ROOT == path or ROOT in path.parents:
        raise ValueError("Private sample must remain outside repository")
    with path.open("rb") as f:
        raw = f.read(MAX_BYTES + 1)
    return inspect_csv(raw)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_exact(url, limit):
    req = Request(url, headers={"User-Agent": "StockwatchResearch/1.0 (+https://stocks.nordl.dev)",
                                "Accept": "*/*"})
    with build_opener(NoRedirect()).open(req, timeout=30) as response:
        if response.geturl() != url:
            raise ValueError("Unexpected redirect")
        raw = response.read(limit+1)
    if len(raw) > limit:
        raise ValueError("Oversized response")
    return raw


def inspect_advertised(region, fetch=fetch_exact):
    # No guessed file paths, no unattended schedule, no writes.
    portal = NAS_PORTALS[region]
    links = nasdaq_links(fetch(portal, MAX_BYTES), region)
    if not links:
        return {"status": "no_recognized_report_links", "region": region,
                "discovered_link_count": 0, "provider_schema_verified": False,
                "quote_normalization_enabled": False, "retention_enabled": False,
                "public_publication": False}
    report = inspect_csv(fetch(links[-1], MAX_BYTES))
    return {**report, "region": region, "discovered_link_count": len(links),
            "sample_downloaded": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--csv", type=Path)
    mode.add_argument("--region", choices=tuple(NAS_PORTALS))
    parser.add_argument("--private-noncommercial", required=True, action="store_true")
    args = parser.parse_args()
    try:
        report = inspect_file(args.csv) if args.csv else inspect_advertised(args.region)
    except HTTPError as exc:
        print(json.dumps({"status": "http_error", "http_status": exc.code,
                          "public_publication": False}))
        return 1
    except (ValueError, OSError) as exc:
        print(json.dumps({"status": "not_validated", "error_type": type(exc).__name__,
                          "public_publication": False}))
        return 1
    print(json.dumps(report, sort_keys=True))
    return 0 if report.get("malformed_row_count") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
