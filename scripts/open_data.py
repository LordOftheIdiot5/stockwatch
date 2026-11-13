"""Official no-key open-data integrations for Stockwatch.

All displayed data is attributed, dated and source-linked. The importer never
generates synthetic observations or treats fuzzy company names as verified IDs.
Run: python scripts/open_data.py --mode daily|weekly|auto
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/open-data.json"
UA = "StockwatchResearch/1.0 (+https://stocks.nordl.dev; public official data)"
COUNTRIES = ("NO", "SE", "DK", "FI", "DE", "FR", "GB", "US", "CN")
META = {
 "norges_bank": ("Norges Bank", "NLOD 2.0", "https://www.norges-bank.no/en/topics/Statistics/open-data/"),
 "ecb": ("European Central Bank", "ECB statistics free reuse, attribution; third-party exceptions", "https://data.ecb.europa.eu/help/api/data-examples"),
 "world_bank": ("World Bank WDI", "CC BY 4.0, subject to indicator-level third-party exceptions", "https://data.worldbank.org/summary-terms-of-use"),
 "eurostat": ("Eurostat", "Eurostat reuse policy; dataset exceptions apply", "https://ec.europa.eu/eurostat/en/web/user-guides/data-browser/api-data-access/api-introduction"),
 "finanstilsynet": ("Finanstilsynet SSR", "NLOD 2.0; only publicly disclosed positions", "https://ssr.finanstilsynet.no/api/v2/"),
 "gleif": ("GLEIF LEI", "CC0 public reference data", "https://www.gleif.org/en/lei-data/gleif-api"),
 "brreg": ("Brønnøysundregistrene", "NLOD 2.0; no personal/role data collected", "https://data.brreg.no/enhetsregisteret/api/dokumentasjon/en/index.html")
}

def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def get_bytes(url, max_bytes=4000000, timeout=20):
    request = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "application/json, text/csv, */*"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError("response_exceeds_size_cap")
        return data

def fetch_json(url, max_bytes=4000000):
    return json.loads(get_bytes(url, max_bytes=max_bytes).decode("utf-8-sig"))

def parse_csv_series(raw, limit=130):
    """Return only explicitly dated, numeric SDMX observations."""
    text = raw.decode("utf-8-sig")
    lines = [line for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if not lines:
        return []
    sample = lines[0]
    dialect = csv.excel
    if sample.count(";") > sample.count(","):
        dialect = csv.excel
        dialect = type("Semi", (csv.excel,), {"delimiter": ";"})
    rows = csv.DictReader(io.StringIO("\n".join(lines)), dialect=dialect)
    out = {}
    for row in rows:
        row = {str(k).strip().upper(): v for k, v in row.items() if k is not None}
        period = (row.get("TIME_PERIOD") or row.get("TIME PERIOD") or row.get("TIME") or "").strip()
        value = row.get("OBS_VALUE") or row.get("OBS VALUE")
        if not re.fullmatch(r"20\d\d-\d\d-\d\d", period or ""):
            continue
        try:
            number = float(str(value).strip())
            if not math.isfinite(number) or number <= 0:
                continue
        except (TypeError, ValueError):
            continue
        out[period] = round(number, 7)
    return [{"date": d, "value": v} for d, v in sorted(out.items())[-limit:]]

def parse_world_bank(payload, indicator, limit=7):
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        raise ValueError("invalid_world_bank_payload")
    by_country = {}
    for rec in payload[1]:
        if not isinstance(rec, dict) or rec.get("value") is None:
            continue
        c = (rec.get("countryiso3code") or "").strip().upper()
        # World Bank may omit ISO-2; prefer the two-letter response field.
        code2 = str((rec.get("country") or {}).get("id") or "").upper()
        if code2 not in COUNTRIES:
            continue
        year = str(rec.get("date") or "")
        if not re.fullmatch(r"20\d\d", year):
            continue
        try:
            val = float(rec["value"])
            if not math.isfinite(val):
                continue
        except (ValueError, TypeError):
            continue
        by_country.setdefault(code2, {})[year] = round(val, 4)
    return {country: [{"date": k + "-01-01", "value": v}
                      for k, v in sorted(years.items())[-limit:]]
            for country, years in by_country.items() if years}

def parse_eurostat(payload, expected_geo="NO"):
    """Decode JSON-stat indices; do not assume a flat array position."""
    if not isinstance(payload, dict) or not isinstance(payload.get("value"), (dict, list)):
        raise ValueError("invalid_eurostat_payload")
    ids, sizes = payload.get("id") or [], payload.get("size") or []
    if len(ids) != len(sizes) or not ids:
        raise ValueError("invalid_eurostat_dimensions")
    dim = payload.get("dimension") or {}
    values = payload["value"]
    result = {}
    for offset_str, val in (enumerate(values) if isinstance(values, list) else values.items()):
        try:
            ix = int(offset_str)
            v = float(val)
            if not math.isfinite(v):
                continue
        except (TypeError, ValueError):
            continue
        coord = {}
        n = ix
        for label, size in reversed(list(zip(ids, sizes))):
            if not isinstance(size, int) or size <= 0:
                raise ValueError("invalid_eurostat_size")
            coord[label] = n % size
            n //= size
        if n:
            continue
        labels = {}
        for label, i in coord.items():
            cat = ((dim.get(label) or {}).get("category") or {}).get("index") or {}
            if isinstance(cat, dict):
                match = next((key for key, order in cat.items() if order == i), None)
            elif isinstance(cat, list):
                match = cat[i] if i < len(cat) else None
            else:
                match = None
            labels[label] = match
        if labels.get("geo") not in (expected_geo, None):
            continue
        period = str(labels.get("time") or "")
        if not re.fullmatch(r"20\d\d-\d\d", period):
            continue
        if labels.get("coicop") not in ("CP00", None) or labels.get("coicop18") not in ("TOTAL", None):
            continue
        if labels.get("unit") not in ("RCH_A", None):
            continue
        result[period] = round(v, 4)
    return [{"date": x + "-01", "value": v} for x, v in sorted(result.items())[-30:]]

def clean_name(s):
    s = unicodedata.normalize("NFKD", str(s or "").casefold())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"\b(asa|as|ab|a/s|oyj|se|ag|sa|plc|nv|holding|holdings)\b", " ", s)
    return " ".join(re.findall(r"[a-z0-9]+", s))

def exact_candidate(requested, records, name_key):
    """Only unique normalized exact legal names qualify even as candidates."""
    norm = clean_name(requested)
    if len(norm) < 4:
        return None
    exact = [r for r in records if isinstance(r, dict) and clean_name(name_key(r)) == norm]
    return exact[0] if len(exact) == 1 else None

def obs(provider, key, label, country, unit, history, source_url, frequency):
    if not history:
        return None
    return {"key": key, "provider": provider, "label": label, "country": country,
            "unit": unit, "frequency": frequency, "period": history[-1]["date"],
            "value": history[-1]["value"], "history": history, "sourceUrl": source_url,
            "observedAt": utcnow(), "license": META[provider][1]}

def fx_norges(currency):
    url = ("https://data.norges-bank.no/api/data/EXR/B." + currency
           + ".NOK.SP?format=csvfile&locale=en&startPeriod="
           + (datetime.now(timezone.utc)-timedelta(days=120)).strftime("%Y-%m-%d"))
    points = parse_csv_series(get_bytes(url))
    return obs("norges_bank", "fx:" + currency + "/NOK", currency + "/NOK reference rate",
               "NO", "NOK per " + currency, points, url, "business_day")

def fx_ecb():
    url = ("https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A"
           "?format=csvdata&lastNObservations=90")
    points = parse_csv_series(get_bytes(url))
    return obs("ecb", "fx:EUR/USD", "EUR/USD reference rate",
               "EU", "USD per EUR", points, url, "business_day")

def world_bank():
    result = []
    ids = [("NY.GDP.MKTP.KD.ZG", "GDP annual growth", "% annual"),
           ("NE.EXP.GNFS.ZS", "Exports of goods and services", "% of GDP")]
    for indicator, label, unit in ids:
        url = ("https://api.worldbank.org/v2/country/" + ";".join(COUNTRIES) +
               "/indicator/" + indicator + "?format=json&date=2019:2026&per_page=500")
        values = parse_world_bank(fetch_json(url), indicator)
        for country, history in values.items():
            x = obs("world_bank", indicator + ":" + country, label, country,
                    unit, history, url, "annual")
            if x:
                result.append(x)
    return result

def eurostat():
    result = []
    for country in ("NO", "SE", "DK", "DE", "FR"):
        url = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
               "prc_hicp_minr?format=JSON&geo=" + country
               + "&coicop18=TOTAL&unit=RCH_A&sinceTimePeriod=2025-01&lang=EN")
        history = parse_eurostat(fetch_json(url), country)
        x = obs("eurostat", "hicp_yoy:" + country,
                "Harmonised consumer prices, annual rate", country,
                "% year-on-year", history, url, "monthly")
        if x:
            result.append(x)
    return result

def public_shorts(root=ROOT):
    url = "https://ssr.finanstilsynet.no/api/v2/instruments"
    data = fetch_json(url, max_bytes=12000000)
    if not isinstance(data, list):
        raise ValueError("invalid_ssr_payload")
    directory = json.loads((root/"data/issuer-identities.json").read_text(encoding="utf8"))
    known = {str(x.get("isin") or "").upper(): x for x in directory.get("entities", [])
             if re.fullmatch("[A-Z]{2}[A-Z0-9]{10}", str(x.get("isin") or "").upper())}
    rows = []
    for item in data:
        isin = str(item.get("isin") or "").upper()
        if isin not in known:
            continue
        events = [e for e in item.get("events") or []
                  if isinstance(e, dict) and isinstance(e.get("date"), str)
                  and isinstance(e.get("shortPercent"), (int, float))]
        if not events:
            continue
        last = max(events, key=lambda e:e["date"])
        rows.append({"ticker": known[isin]["ticker"], "isin": isin,
                     "date": last["date"], "publicShortPercent": last["shortPercent"],
                     "sourceUrl": url, "license": META["finanstilsynet"][1]})
    return {"trackedInRegister": len(data), "matchedByVerifiedIsin": rows,
            "note": "Only public ≥0.5% positions; absence is not zero short interest.",
            "sourceUrl": url}

def gleif_candidate(name):
    url = ("https://api.gleif.org/api/v1/lei-records?" +
           urllib.parse.urlencode({"filter[entity.legalName]": name, "page[size]": 10}))
    data = fetch_json(url)
    records = data.get("data") or []
    record = exact_candidate(name, records,
                             lambda r: ((r.get("attributes") or {}).get("entity") or {}).get("legalName", {}).get("name", ""))
    if not record:
        return None
    attr = record.get("attributes") or {}
    entity = attr.get("entity") or {}
    reg = attr.get("registration") or {}
    return {"provider": "gleif", "lei": attr.get("lei") or record.get("id"),
            "legalName": (entity.get("legalName") or {}).get("name"),
            "registrationStatus": reg.get("status"),
            "sourceUrl": "https://api.gleif.org/api/v1/lei-records/" + str(record.get("id") or ""),
            "verified": False, "match": "unique_normalized_exact_name_candidate"}

def brreg_candidate(name):
    url = ("https://data.brreg.no/enhetsregisteret/api/enheter?" +
           urllib.parse.urlencode({"navn": name, "size": 15}))
    data = fetch_json(url)
    records = (data.get("_embedded") or {}).get("enheter") or []
    record = exact_candidate(name, records, lambda r:r.get("navn"))
    if not record:
        return None
    org = str(record.get("organisasjonsnummer") or "")
    if not re.fullmatch(r"\d{9}", org):
        return None
    return {"provider": "brreg", "orgNumber": org, "legalName": record.get("navn"),
            "registrationStatus": "registered" if record.get("registrertIForetaksregisteret") else "not_flagged",
            "sourceUrl": "https://data.brreg.no/enhetsregisteret/api/enheter/" + org,
            "verified": False, "match": "unique_normalized_exact_name_candidate"}

def identity_candidates(previous, watchlist, limit=12):
    old = previous.get("identityCandidates") or []
    lookups = previous.get("identityLookups") or []
    existing = {(x.get("ticker"), x.get("provider")) for x in lookups}
    existing.update((x.get("ticker"), x.get("provider")) for x in old)
    out = list(old)
    attempted = {"gleif": 0, "brreg": 0}
    errors = {"gleif": [], "brreg": []}
    rows = watchlist.get("tickers") or []
    for row in rows:
        ticker, name = row.get("ticker"), row.get("name")
        if not ticker or not name:
            continue
        for provider, fn in (("gleif", gleif_candidate), ("brreg", brreg_candidate)):
            if provider == "brreg" and not ticker.endswith(".OL"):
                continue
            if attempted[provider] >= limit or (ticker, provider) in existing:
                continue
            attempted[provider] += 1
            try:
                candidate = fn(name)
                if candidate:
                    candidate.update(ticker=ticker, searchedName=name, checkedAt=utcnow())
                    out.append(candidate)
                lookups.append({"ticker":ticker,"provider":provider,"checkedAt":utcnow(),
                                "result":"candidate" if candidate else "no_unique_match"})
                existing.add((ticker, provider))
            except (OSError, ValueError, KeyError, TypeError) as error:
                errors[provider].append(type(error).__name__)
            time.sleep(0.2)
    return out[:300], lookups[:400], attempted, errors

def build(root=ROOT, mode="auto", now=None):
    dest = root / "data/open-data.json"
    now = now or datetime.now(timezone.utc)
    if mode == "auto":
        mode = "weekly" if now.weekday() == 0 else "daily"
    try:
        previous = json.loads(dest.read_text(encoding="utf8"))
    except (OSError, ValueError):
        previous = {}
    stored = {x["key"]:x for x in previous.get("series") or [] if x.get("key")}
    statuses = {x["id"]:x for x in previous.get("sources") or [] if x.get("id")}
    for provider, (name, license, url) in META.items():
        statuses.setdefault(provider, {"id":provider, "name":name, "license":license, "documentation":url,
                                       "status":"not_checked", "lastSuccessAt":None})
    tasks = [
        ("norges_bank", lambda:[fx_norges("USD"),fx_norges("EUR")]),
        ("ecb", lambda:[fx_ecb()]),
        ("world_bank", world_bank),
        ("eurostat", eurostat),
        ("finanstilsynet", lambda:public_shorts(root)),
    ]
    shorts = previous.get("publicShorts") or None
    for provider, action in tasks:
        status = statuses[provider]
        status["lastAttemptAt"] = utcnow()
        try:
            values = action()
            if provider == "finanstilsynet":
                shorts = values
                count = len(values.get("matchedByVerifiedIsin") or [])
                # A successful registry call is valid even with no ISIN crossmatches.
                count = count or values.get("trackedInRegister", 0)
            else:
                for item in values:
                    if item:
                        stored[item["key"]] = item
                count = sum(bool(item) for item in values)
            if count:
                status.update(status="ok", lastSuccessAt=utcnow(), records=count, error=None)
            else:
                status.update(status="empty", error="no_valid_records")
        except (OSError, ValueError, KeyError, TypeError, urllib.error.HTTPError) as error:
            status.update(status="error", error=type(error).__name__)
    candidates = previous.get("identityCandidates") or []
    lookups = previous.get("identityLookups") or []
    if mode == "weekly":
        directory = json.loads((root/"watchlist.json").read_text(encoding="utf8"))
        candidates, lookups, attempted, errors = identity_candidates(previous, directory)
        for provider in ("gleif", "brreg"):
            status = statuses[provider]
            status["lastAttemptAt"] = utcnow()
            if errors[provider]:
                status.update(status="partial_error", error="some_requests_failed",
                              lastSuccessAt=status.get("lastSuccessAt"))
            else:
                status.update(status="ok", lastSuccessAt=utcnow(), error=None)
            status["attempted"] = attempted[provider]
            status["candidates"] = sum(x.get("provider")==provider for x in candidates)
    result = {"generated":utcnow(), "mode":mode,
              "notice":"Official statistical series, not tradable live security prices or freight quotations.",
              "series":sorted(stored.values(),key=lambda x:x["key"]),
              "sources":sorted(statuses.values(),key=lambda x:x["id"]),
              "identityCandidates":candidates,
              "identityLookups":lookups,
              "identityNote":"Unverified name-search suggestions, never automatically linked to issuers.",
              "publicShorts":shorts}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("Official open data: {} series; {} candidate identity matches; source status: {}".format(
        len(stored),len(candidates),",".join(x["id"]+"="+x["status"] for x in result["sources"])))
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("auto","daily","weekly"), default="auto")
    args = parser.parse_args()
    build(mode=args.mode)
