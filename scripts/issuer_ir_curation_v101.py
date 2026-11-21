"""V101d offline issuer-link triage: reviewable actual-file vs landing-page candidates.

Does NOT fetch document bytes, assert archive rights, or extract financial facts.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from issuer_ir_reports_v101 import hostname, validate_registry

ROOT = Path(__file__).resolve().parents[1]
MAX_ROWS = 5000
FILE_SUFFIX = {".pdf": "pdf", ".zip": "structured_archive",
               ".xlsx": "spreadsheet", ".xls": "spreadsheet", ".xhtml": "xhtml"}

def classify_link(link):
    parts = urlsplit(link)
    path = parts.path.lower()
    for ext, label in FILE_SUFFIX.items():
        if path.endswith(ext):
            return "direct_file", label
    if parts.hostname in ("ml-eu.globenewswire.com",) and "/resource/download/" in path:
        return "opaque_download", "unknown_type_requires_header_check"
    if re.search(r"/investor/results-webcast/(?:20\d{2})/", path) or re.search(r"/(?:reports|results)/20\d{2}/", path):
        return "report_landing_page", "html_follow_up"
    return "other_page", "not_a_verified_document"

def curate(payload, registry):
    if not isinstance(payload, dict) or payload.get("schemaVersion") != 1:
        raise ValueError("Unsupported issuer discovery dataset")
    sources = validate_registry(registry)
    issuers = {row["ticker"]: row for row in sources}
    rows = payload.get("items")
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ValueError("Invalid or oversized candidate list")
    seen, items, discarded = set(), [], []
    by_type, by_issuer = Counter(), defaultdict(Counter)
    for obj in rows:
        if not isinstance(obj, dict):
            raise ValueError("Invalid candidate row")
        ticker = obj.get("ticker")
        issuer = issuers.get(ticker)
        if issuer is None or obj.get("sourcePage") != issuer["landingPage"]:
            raise ValueError("Candidate not tied to reviewed original issuer source")
        url = obj.get("documentUrl")
        if not isinstance(url, str) or hostname(url) not in issuer["allowedHosts"]:
            raise ValueError("Candidate URL escapes approved source domains")
        if obj.get("documentDownloaded") is not False or obj.get("privateRetentionApproved") is not False:
            raise ValueError("Discovery data must not claim downloaded or licensed documents")
        key = (ticker, url)
        if key in seen:
            continue
        seen.add(key)
        typ, format_guess = classify_link(url)
        by_type[typ] += 1
        by_issuer[ticker][typ] += 1
        base = {
            "ticker": ticker, "issuer": issuer["issuer"],
            "sourcePage": issuer["landingPage"], "documentUrl": url,
            "linkText": (obj.get("linkText") or "")[:220],
            "kindCandidate": obj.get("kindCandidate"), 
            "fiscalYearCandidate": obj.get("fiscalYearCandidate"),
            "quarterCandidate": obj.get("quarterCandidate"),
            "publishedAt": None,
            "linkKind": typ, "formatCandidate": format_guess,
            "verifiedDocument": False, "documentStored": False,
            "privateRetentionApproved": False, "publicDisplayApproved": False,
            "reviewStatus": "human_and_rights_review_required"
        }
        if typ == "other_page":
            discarded.append({"ticker": ticker, "documentUrl": url, "reason": "no_document_evidence"})
        else:
            items.append(base)
    if len(items) + len(discarded) != len(seen):
        raise ValueError("Unbalanced candidate classifications")
    items.sort(key=lambda r: (r["ticker"], {"direct_file": 0, "opaque_download": 1, "report_landing_page": 2}[r["linkKind"]],
                                  -(r["fiscalYearCandidate"] or 0), r["documentUrl"]))
    return {
        "schemaVersion": 1,
        "generated": payload.get("generated"),
        "sourceCount": len(sources), "inputCandidateCount": len(seen),
        "reviewQueueCount": len(items), "discardedCount": len(discarded),
        "byLinkType": dict(sorted(by_type.items())),
        "byIssuer": {k: dict(sorted(v.items())) for k, v in sorted(by_issuer.items())},
        "items": items, "discarded": discarded,
        "notice": "Curation of original link candidates only; these are not verified reports, stored document bytes or licensed financial facts."
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--registry", type=Path, default=ROOT/"scripts/issuer_ir_sources_v101.json")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.input.stat().st_size > 5 * 1024 * 1024:
        p.error("Candidate discovery exceeds bounded size")
    result = curate(json.loads(a.input.read_text()), json.loads(a.registry.read_text()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("inputCandidateCount", "reviewQueueCount", "discardedCount", "byLinkType", "byIssuer")}, sort_keys=True))

if __name__ == "__main__":
    main()
