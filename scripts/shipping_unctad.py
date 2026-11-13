"""UNCTAD monthly liner shipping connectivity (LSCI); NOT freight quotations.

Downloads the official no-key 7z bulk CSV. Requires py7zr at runtime.
Reuse: CC BY 3.0 IGO with UNCTAD Data Hub attribution.
"""
from __future__ import annotations
import csv
import io
import json
import math
import re
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = "data/shipping-connectivity.json"
SOURCE = "https://unctadstat.unctad.org/datacentre/dataviewer/US.LSCI_M"
BULK = "https://unctadstat-api.unctad.org/bulkdownload/US.LSCI_M/US_LSCI_M"
TERMS = "https://unctadstat.unctad.org/EN/About.html#TERMS_OF_USE"
LICENSE = "CC BY 3.0 IGO — United Nations Trade and Development Data Hub (UNCTADstat)"
COUNTRIES = {
    "China": ("China",),
    "South Korea": ("Republic of Korea", "Korea, Republic of", "South Korea"),
    "Singapore": ("Singapore",),
    "United States": ("United States of America", "United States"),
    "Malaysia": ("Malaysia",),
    "Germany": ("Germany",),
    "Netherlands": ("Netherlands",),
    "Norway": ("Norway",),
    "Sweden": ("Sweden",),
    "Denmark": ("Denmark",),
    "India": ("India",),
    "Japan": ("Japan",),
    "United Kingdom": ("United Kingdom",),
    "United Arab Emirates": ("United Arab Emirates",),
    "Viet Nam": ("Viet Nam", "Vietnam"),
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def norm(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def fetch_csv():
    """Never fetch arbitrary URLs. No archive member may escape its temp directory."""
    try:
        import py7zr
    except ImportError as error:
        raise RuntimeError("py7zr_not_installed") from error
    req = urllib.request.Request(
        BULK, headers={"User-Agent": "StockwatchResearch/1.0 (+https://stocks.nordl.dev)",
                       "Accept": "application/octet-stream"})
    with urllib.request.urlopen(req, timeout=70) as response:
        binary = response.read(3000001)
    if not binary or len(binary) > 3000000:
        raise ValueError("unctad_archive_too_large_or_empty")
    with tempfile.TemporaryDirectory() as temp:
        archive = Path(temp) / "data.7z"
        archive.write_bytes(binary)
        with py7zr.SevenZipFile(archive, mode="r") as package:
            names = package.getnames()
            choices = [n for n in names if n.lower().endswith(".csv")]
            if len(choices) != 1 or choices[0] != Path(choices[0]).name:
                raise ValueError("unctad_unexpected_archive_members")
            package.extract(path=temp, targets=choices)
        csv_file = Path(temp) / choices[0]
        if csv_file.stat().st_size > 10000000:
            raise ValueError("unctad_csv_too_large")
        return csv_file.read_text(encoding="utf-8-sig")


def parse_csv(raw):
    reader = csv.DictReader(io.StringIO(raw))
    columns = reader.fieldnames or []
    month = next((x for x in columns if norm(x) == "month"), None)
    economy = next((x for x in columns if norm(x) == "economylabel"), None)
    if not economy:
        economy = next((x for x in columns if norm(x) == "economy"), None)
    index = next((x for x in columns
                  if norm(x).startswith("index") and "2023" in norm(x)
                  and not ("footnote" in norm(x) or "missingvalue" in norm(x))), None)
    if not all((month, economy, index)):
        raise ValueError("unctad_unrecognized_csv_headers: " + ",".join(columns)[:300])
    alias = {norm(a): label for label, aliases in COUNTRIES.items() for a in aliases}
    grouped = {k: {} for k in COUNTRIES}
    for row in reader:
        label = alias.get(norm(row.get(economy)))
        if label is None:
            continue
        period = str(row.get(month) or "").strip()
        match = re.fullmatch(r"(20\d{2})M(0[1-9]|1[0-2])", period)
        if not match:
            continue
        try:
            value = float(str(row.get(index) or "").replace(",", "").strip())
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value) or value <= 0 or value > 100000:
            continue
        grouped[label][f"{match[1]}-{match[2]}-01"] = round(value, 5)
    return {key: [{"date": date, "value": value}
                  for date, value in sorted(history.items())][-180:]
            for key, history in grouped.items()}


def build(root=ROOT):
    output_path = root / OUT
    try:
        previous = json.loads(output_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        previous = {}
    try:
        data = parse_csv(fetch_csv())
        valid = {k: values for k, values in data.items() if len(values) >= 2}
        if len(valid) < 10:
            raise ValueError("unctad_insufficient_country_history")
        series = []
        for name in COUNTRIES:
            history = valid.get(name)
            if not history:
                continue
            series.append({
                "key": "unctad:lsci-monthly:" + re.sub(r"[^a-z]", "-", name.lower()),
                "label": name + " liner shipping connectivity",
                "country": name,
                "unit": "index, Q1 2023 average = 100",
                "frequency": "monthly",
                "category": "Liner shipping connectivity",
                "sourceUrl": SOURCE,
                "provider": "United Nations Trade and Development Data Hub",
                "license": LICENSE,
                "licenseUrl": TERMS,
                "period": history[-1]["date"][:7],
                "value": history[-1]["value"],
                "history": history,
                "observedAt": now(),
                "isActualRate": False,
                "isBalticBenchmark": False,
            })
        status = {"status": "ok", "sourceUrl": SOURCE,
                  "lastSuccessAt": now(), "series": len(series),
                  "observations": sum(len(x["history"]) for x in series)}
    except Exception as error:
        series = previous.get("series") or []
        prior = previous.get("source") or {}
        status = {"status": "error", "sourceUrl": SOURCE,
                  "lastSuccessAt": prior.get("lastSuccessAt"),
                  "errorType": type(error).__name__,
                  "note": "Earlier dated observations preserved; source did not refresh."}
        if isinstance(error, urllib.error.HTTPError):
            status["httpStatus"] = error.code
    result = {
        "generated": now(),
        "notice": "UNCTAD monthly liner-network connectivity index; NOT spot freight prices, container costs, or daily vessel movements.",
        "source": status, "series": series,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    catalog_path = root / "data/dataset-catalog.json"
    if catalog_path.exists():
        try:
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            old = catalog.get("datasets") or []
            catalog["datasets"] = [
                item for item in old if item.get("path") != OUT
            ] + [{"name": "UNCTAD monthly liner shipping connectivity",
                  "path": OUT, "records": sum(len(x.get("history") or []) for x in series),
                  "license": LICENSE}]
            catalog["generated"] = now()
            catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
        except (OSError, ValueError, TypeError):
            pass
    print("UNCTAD LSCI: " + status["status"] + "; series=" + str(len(series)))
    return result


if __name__ == "__main__":
    build()
