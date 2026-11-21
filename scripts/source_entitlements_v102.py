"""V102 fail-closed, source-specific market-data entitlement preflight.

This registry is a review queue, not a licence or a source of market quotes.
Future adapters must call require_permission before ingestion or publication.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
DEFAULT_REGISTRY = ROOT / "source_entitlements_v102.json"
CAPABILITIES = ("productionCollection", "privateRetention", "publicDisplay", "commercialExport")
IDENTITIES = ("isinMapped", "micMapped", "currencyVerified", "sessionCloseVerified")


class EntitlementError(ValueError):
    pass


def _valid_https(url):
    if not isinstance(url, str):
        return False
    parts = urlsplit(url)
    return parts.scheme == "https" and bool(parts.netloc) and not parts.username and not parts.password


def validate(registry):
    if not isinstance(registry, dict) or registry.get("schemaVersion") != 1:
        raise EntitlementError("Unsupported source-entitlement registry version")
    if not isinstance(registry.get("sources"), list) or not registry["sources"]:
        raise EntitlementError("Source registry must contain entries")
    seen = set()
    for source in registry["sources"]:
        if not isinstance(source, dict):
            raise EntitlementError("Source entry is invalid")
        sid = source.get("id")
        if not isinstance(sid, str) or not sid or sid in seen:
            raise EntitlementError("Source id missing or repeated")
        seen.add(sid)
        if not all(_valid_https(source.get(k)) for k in ("sourceUrl", "policyUrl")):
            raise EntitlementError("Source and policy URLs must be original HTTPS URLs: " + sid)
        if not all(isinstance(source.get(k), str) and source[k].strip()
                   for k in ("provider", "product", "observationKind", "reviewStatus", "policyFinding")):
            raise EntitlementError("Missing source evidence: " + sid)
        if not isinstance(source.get("venues"), list) or not source["venues"]:
            raise EntitlementError("Venue list missing: " + sid)
        try:
            date.fromisoformat(source["reviewedAt"])
        except (KeyError, TypeError, ValueError):
            raise EntitlementError("Invalid source review date: " + sid)
        rights = source.get("permissions")
        if not isinstance(rights, dict) or set(rights) != set(CAPABILITIES):
            raise EntitlementError("Incomplete rights matrix: " + sid)
        if not all(type(value) is bool for value in rights.values()):
            raise EntitlementError("Rights must be explicit booleans: " + sid)
        ident = source.get("identity")
        if not isinstance(ident, dict) or set(ident) != set(IDENTITIES):
            raise EntitlementError("Missing verified identity flags: " + sid)
        if not all(type(value) is bool for value in ident.values()):
            raise EntitlementError("Identity flags must be explicit booleans: " + sid)
        if any(rights.values()):
            auth = source.get("authorization")
            if not isinstance(auth, dict) or not all(
                isinstance(auth.get(k), str) and auth[k].strip()
                for k in ("evidenceRef", "scope", "reviewer", "reviewedOn")
            ):
                raise EntitlementError("Enabled rights require scoped approval evidence: " + sid)
            if auth.get("sourceId") != sid or auth.get("product") != source["product"]:
                raise EntitlementError("Approval must identify the exact source and product: " + sid)
            granted = {name for name, enabled in rights.items() if enabled}
            capabilities = auth.get("capabilities")
            if not isinstance(capabilities, list) or set(capabilities) != granted or len(capabilities) != len(granted):
                raise EntitlementError("Approval capabilities must exactly match enabled uses: " + sid)
            try:
                date.fromisoformat(auth["reviewedOn"])
            except (TypeError, ValueError):
                raise EntitlementError("Approval date is invalid: " + sid)
        elif source.get("authorization") is not None:
            raise EntitlementError("Unapproved source cannot claim authorization: " + sid)
    return registry


def load(path=DEFAULT_REGISTRY):
    with open(path, encoding="utf-8") as file:
        return validate(json.load(file))


def require_permission(source_id, capability, registry=None):
    """Deny unknown products and unapproved uses; return the approved source row."""
    if capability not in CAPABILITIES:
        raise EntitlementError("Unrecognized capability: " + str(capability))
    validated = validate(registry) if registry is not None else load()
    source = next((item for item in validated["sources"] if item["id"] == source_id), None)
    if source is None or source["permissions"][capability] is not True:
        raise PermissionError("Market-data entitlement not approved: " + str(source_id) + "/" + capability)
    return source


def main():
    parser = argparse.ArgumentParser(description="V102 rights review; never enables a feed")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--source")
    parser.add_argument("--capability", choices=CAPABILITIES)
    args = parser.parse_args()
    data = load(args.registry)
    if bool(args.source) != bool(args.capability):
        parser.error("--source and --capability are required together")
    if args.source:
        try:
            require_permission(args.source, args.capability, data)
        except PermissionError as error:
            print(str(error))
            return 2
        print("Approval recorded for that scoped capability; verify underlying evidence before use.")
    else:
        print(json.dumps({"sources": len(data["sources"]),
                          "approvedCapabilities": sum(sum(x["permissions"].values()) for x in data["sources"]),
                          "notice": "No source was activated by this inspection."}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
