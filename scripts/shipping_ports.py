"""Import World Bank WDI container-port throughput (annual TEUs), not freight prices.

The IS.SHP.GOOD.TU indicator page expressly labels the series CC BY 4.0.
Its original data source is UNCTAD. Attribution and the source URL travel
with every observation. Never present TEU throughput as a daily rate.
"""
from __future__ import annotations

import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = "data/shipping-ports.json"
INDICATOR = "IS.SHP.GOOD.TU"
SOURCE = "https://data.worldbank.org/indicator/" + INDICATOR
TERMS = "https://www.worldbank.org/ext/en/legal/terms-conditions/datasets"
LICENSE = "CC BY 4.0 — World Bank WDI / UNCTAD-origin indicator; attribution required"
COUNTRIES = {
    "WLD": "World", "CHN": "China", "SGP": "Singapore",
    "USA": "United States", "NLD": "Netherlands", "DEU": "Germany",
    "NOR": "Norway", "SWE": "Sweden", "DNK": "Denmark",
    "GBR": "United Kingdom", "JPN": "Japan", "KOR": "South Korea",
    "IND": "India", "ARE": "United Arab Emirates", "VNM": "Viet Nam",
}
USER_AGENT = "StockwatchResearch/1.0 (+https://stocks.nordl.dev)"


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def api_url():
    codes = ";".join(COUNTRIES)
    return ("https://api.worldbank.org/v2/country/" + codes + "/indicator/" +
            INDICATOR + "?" + urllib.parse.urlencode({
                "format": "json", "per_page": 2000, "date": "2005:2026"
            }))


def fetch_rows():
    request = urllib.request.Request(
        api_url(), headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=35) as response:
                raw = response.read(1500001)
                if len(raw) > 1500000:
                    raise ValueError("worldbank_response_too_large")
            payload = json.loads(raw)
            if (not isinstance(payload, list) or len(payload) != 2 or
                    not isinstance(payload[0], dict) or
                    not isinstance(payload[1], list)):
                raise ValueError("worldbank_invalid_response")
            if int(payload[0].get("pages", 0)) != 1:
                raise ValueError("worldbank_unfetched_pages")
            return payload[1]
        except urllib.error.HTTPError as error:
            if attempt or error.code not in (429, 500, 502, 503, 504):
                raise
        except (TimeoutError, urllib.error.URLError):
            if attempt:
                raise
        time.sleep(2)
    raise RuntimeError("worldbank_unreachable")


def valid_rows(rows):
    """Require the exact indicator, known countries, real years and finite TEUs."""
    if not isinstance(rows, list):
        raise ValueError("worldbank_invalid_rows")
    points = {code: {} for code in COUNTRIES}
    for row in rows:
        if not isinstance(row, dict):
            continue
        indicator = row.get("indicator")
        if not isinstance(indicator, dict) or indicator.get("id") != INDICATOR:
            continue
        code = row.get("countryiso3code")
        if code not in COUNTRIES:
            continue
        year = str(row.get("date", ""))
        if not re.fullmatch(r"20\d{2}", year) or int(year) > 2026:
            continue
        try:
            number = float(row.get("value"))
        except (ValueError, TypeError):
            continue
        if not math.isfinite(number) or number <= 0 or number > 1e12:
            continue
        points[code][year + "-12-31"] = round(number, 3)
    return {code: [{"date": date, "value": value}
                   for date, value in sorted(annual.items())]
            for code, annual in points.items()}


def build(root=ROOT):
    path = root / OUT
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    try:
        parsed = valid_rows(fetch_rows())
        # Require meaningful global coverage: a sparse/partial upstream response
        # is an error, not a successful refresh that wipes existing countries.
        populated = [code for code, history in parsed.items() if len(history) >= 2]
        if "WLD" not in populated or len(populated) < 5:
            raise ValueError("worldbank_insufficient_port_coverage")
        series = []
        for code, name in COUNTRIES.items():
            history = parsed[code]
            if not history:
                continue
            series.append({
                "key": "worldbank:container-port-teu:" + code,
                "countryCode": code, "label": name + " container port throughput",
                "provider": "World Bank WDI (source: UNCTAD)",
                "category": "Container port activity", "unit": "TEU",
                "frequency": "annual", "sourceUrl": SOURCE, "licenseUrl": TERMS,
                "license": LICENSE, "period": history[-1]["date"][:4],
                "value": history[-1]["value"], "history": history,
                "observedAt": timestamp(), "isActualRate": False,
                "isBalticBenchmark": False,
            })
        status = {
            "status": "ok", "sourceUrl": SOURCE, "lastSuccessAt": timestamp(),
            "series": len(series),
            "observations": sum(len(s["history"]) for s in series),
        }
    except Exception as error:
        series = previous.get("series") or []
        prior = previous.get("source") or {}
        status = {
            "status": "error", "sourceUrl": SOURCE,
            "lastSuccessAt": prior.get("lastSuccessAt"),
            "errorType": type(error).__name__,
            "note": "Previous observations retained with their original dates; not refreshed.",
        }
        if isinstance(error, urllib.error.HTTPError):
            status["httpStatus"] = int(error.code)
    output = {
        "generated": timestamp(),
        "notice": "Annual country container-port throughput in TEUs; NOT spot freight rates, charter earnings, daily vessel movements or Baltic benchmarks.",
        "source": status, "series": series,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    catalog_path = root / "data/dataset-catalog.json"
    if catalog_path.exists():
        try:
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            old = catalog.get("datasets") or []
            entry = {
                "name": "World Bank annual container-port traffic (TEU)",
                "path": OUT, "records": sum(len(s.get("history") or []) for s in series),
                "license": LICENSE,
            }
            catalog["datasets"] = [x for x in old if x.get("path") != OUT] + [entry]
            catalog["generated"] = timestamp()
            catalog_path.write_text(
                json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except (OSError, ValueError, TypeError):
            pass
    print("World Bank port throughput: " + status["status"] + "; series=" + str(len(series)))
    return output


if __name__ == "__main__":
    build()
