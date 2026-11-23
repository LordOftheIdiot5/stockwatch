"""V120 limited, read-only Fintraffic AIS proof: no public fleet publication.

Only a specifically requested MMSI can be fetched. The output is an optional
local source-dated observation, NOT a live ship layer, a track, a port arrival,
or a source-verified company relationship. Fintraffic CC BY 4.0 attribution
must accompany any authorized downstream publishing.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://meri.digitraffic.fi/api/ais/v1"
TERMS = "https://www.digitraffic.fi/en/terms-of-service/"
LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
MAX_POSITION_AGE_MS = 30 * 60 * 1000
FUTURE_TOLERANCE_MS = 2 * 60 * 1000
MAX_RESPONSE_BYTES = 1_000_000
APP_HEADER = "Nordl/Stockwatch AIS research 1.0"


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat(
        timespec="seconds"
    ).replace("+00:00", "Z")


def mmsi_number(value: object) -> int | None:
    """Accept exactly nine digits, excluding blank/zero AIS identifiers."""
    value = str(value)
    return int(value) if re.fullmatch(r"[1-9][0-9]{8}", value) else None


def numeric(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def normalize(feature: object, metadata: object = None, now_ms: int | None = None) -> dict | None:
    """Reject stale, invalid or mismatched data; never interpolate a position."""
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    if not isinstance(feature, dict) or feature.get("type") != "Feature":
        return None
    prop, geom = feature.get("properties"), feature.get("geometry")
    if not isinstance(prop, dict) or not isinstance(geom, dict):
        return None
    if geom.get("type") != "Point":
        return None
    coords = geom.get("coordinates")
    if not isinstance(coords, list) or len(coords) < 2:
        return None
    lon, lat = numeric(coords[0]), numeric(coords[1])
    if lon is None or lat is None or not (-180 <= lon <= 180 and -90 <= lat <= 90):
        return None
    mmsi = mmsi_number(prop.get("mmsi", feature.get("mmsi")))
    if mmsi is None or (feature.get("mmsi") is not None and mmsi_number(feature["mmsi"]) != mmsi):
        return None
    timestamp = numeric(prop.get("timestampExternal"))
    if timestamp is None or not 1_577_836_800_000 <= timestamp <= now_ms + FUTURE_TOLERANCE_MS:
        return None
    if now_ms - timestamp > MAX_POSITION_AGE_MS:
        return None
    speed = numeric(prop.get("sog"))
    speed = speed if speed is not None and 0 <= speed < 102.3 else None  # AIS 102.3 = unavailable
    course = numeric(prop.get("cog"))
    course = course if course is not None and 0 <= course < 360 else None
    heading = numeric(prop.get("heading"))
    heading = int(heading) if heading is not None and 0 <= heading < 360 else None
    status = prop.get("navStat")
    status = status if type(status) is int and 0 <= status <= 15 else None

    meta = metadata if isinstance(metadata, dict) and mmsi_number(metadata.get("mmsi")) == mmsi else {}
    name = meta.get("name") if isinstance(meta.get("name"), str) else None
    destination = meta.get("destination") if isinstance(meta.get("destination"), str) else None
    name = name.strip()[:120] or None if name is not None else None
    destination = destination.strip()[:60] or None if destination is not None else None
    meta_time = numeric(meta.get("timestamp"))
    if meta_time is not None and not 1_577_836_800_000 <= meta_time <= now_ms + FUTURE_TOLERANCE_MS:
        meta_time = None

    return {
        "mmsi": mmsi, "name": name, "destinationAisReported": destination,
        "longitude": lon, "latitude": lat,
        "speedKnots": speed, "courseDegrees": course, "headingDegrees": heading,
        "navigationStatusCode": status,
        "positionReportedAt": iso(int(timestamp)),
        "metadataReportedAt": iso(int(meta_time)) if meta_time is not None else None,
        "source": "Fintraffic Digitraffic", "sourceUrl": API + "/locations",
        "dataLicense": "CC BY 4.0", "licenseUrl": LICENSE_URL,
        "coverage": "Finnish AIS receiver coverage; not global",
        "destinationCaveat": "AIS-transmitted destination is not a confirmed itinerary",
    }


def snapshot(location_payload: object, metadata: object, requested_mmsi: int,
             now_ms: int | None = None) -> dict:
    """One-MMSI source snapshot. An invalid/stale record produces an empty list."""
    now_ms = int(time.time() * 1000) if now_ms is None else int(now_ms)
    if mmsi_number(requested_mmsi) is None:
        raise ValueError("invalid_mmsi")
    if not isinstance(location_payload, dict) or location_payload.get("type") != "FeatureCollection":
        raise ValueError("invalid_fintraffic_payload")
    features = location_payload.get("features")
    if not isinstance(features, list) or len(features) > 10_000:
        raise ValueError("invalid_fintraffic_features")
    candidates = [
        row for f in features
        if (row := normalize(f, metadata, now_ms)) is not None and row["mmsi"] == requested_mmsi
    ]
    candidates.sort(key=lambda r: r["positionReportedAt"], reverse=True)
    return {
        "schemaVersion": 1, "provider": "Fintraffic Digitraffic",
        "source": API + "/locations", "termsUrl": TERMS,
        "license": "CC BY 4.0", "licenseUrl": LICENSE_URL,
        "attribution": "Source: Fintraffic / digitraffic.fi, license CC 4.0 BY",
        "retrievedAt": iso(now_ms),
        "kind": "AIS position snapshot, NOT continuous live tracking",
        "requestedMmsi": requested_mmsi,
        "positions": candidates[:1],
        "reason": None if candidates else "no_fresh_verified_position",
        "coverage": "Finnish AIS receiver coverage; not global",
        "redistributionState": "private_integration_pilot_not_published",
    }


def fetch_json(url: str) -> object:
    if not url.startswith(API + "/"):
        raise ValueError("non_allowlisted_api")
    request = urllib.request.Request(
        url, headers={
            "Digitraffic-User": APP_HEADER, "Accept-Encoding": "gzip",
            "Accept": "application/json",
        }
    )
    with urllib.request.urlopen(request, timeout=18) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ValueError("upstream_response_too_large")
        if response.headers.get("Content-Encoding", "").lower() == "gzip":
            raw = gzip.decompress(raw)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError("decompressed_response_too_large")
    return json.loads(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mmsi", required=True, help="Single 9-digit MMSI; never broad public tracking")
    parser.add_argument("--out", required=True, type=Path, help="Private local JSON file, never public/data/")
    args = parser.parse_args()
    mmsi = mmsi_number(args.mmsi)
    if mmsi is None:
        parser.error("MMSI must contain exactly nine digits")
    # Keep real AIS responses outside the web-published GitHub checkout entirely.
    if args.out.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error("Pilot AIS snapshots must be written outside the Stockwatch repository")
    locations = fetch_json(API + "/locations?mmsi=" + str(mmsi))
    try:
        vessel = fetch_json(API + "/vessels/" + str(mmsi))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        vessel = None  # keep genuine position; never invent missing identity
    output = snapshot(locations, vessel, mmsi)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("provider=Fintraffic positions=" + str(len(output["positions"])) + " pilot_only=true")


if __name__ == "__main__":
    main()
