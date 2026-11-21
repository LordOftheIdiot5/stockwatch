"""V101 issuer-owned IR report discovery: strictly metadata-only, never auto-download documents.

Network is opt-in, bounded, robots-aware and restricted to manually reviewed IR pages.
Source links are document CANDIDATES, not verified corporate facts or archival rights.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import ipaddress
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit, urldefrag
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "scripts/issuer_ir_sources_v101.json"
UA = "Nordl-Stockwatch-IR-Discovery/1.0 (+https://stocks.nordl.dev/; metadata only)"
MAX_SOURCES = 6
MAX_HTML_BYTES = 1_500_000
ALLOWED_FILE_EXTENSIONS = (".pdf", ".zip", ".xlsx", ".xls", ".xhtml")
REPORT_PATTERN = re.compile(
    r"\b(annual|quarterly|half[ -]?year|interim|financial|results?|sustainability|esef|investor|presentation|q[1-4])\b",
    re.IGNORECASE,
)
YEAR_PATTERN = re.compile(r"\b20(?:1\d|2\d|3\d)\b")
QUARTER_PATTERN = re.compile(r"\bQ([1-4])\b", re.IGNORECASE)


def hostname(url):
    if not isinstance(url, str):
        return ""
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.port not in (None, 443):
        return ""
    name = parts.hostname.lower()
    if name in ("localhost",) or name.endswith((".localhost", ".local", ".internal")):
        return ""
    try:
        ipaddress.ip_address(name)
        return ""
    except ValueError:
        pass
    if not re.fullmatch(r"[a-z0-9.-]+", name) or "." not in name or ".." in name:
        return ""
    return name


def validate_registry(data):
    if not isinstance(data, dict) or data.get("schemaVersion") != 1:
        raise ValueError("unsupported_issuer_ir_registry")
    rows = data.get("sources")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_SOURCES:
        raise ValueError("issuer_ir_source_bound")
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("ticker"), str) or not row["ticker"]:
            raise ValueError("invalid_issuer")
        if row["ticker"] in seen:
            raise ValueError("duplicate_issuer")
        seen.add(row["ticker"])
        hosts = row.get("allowedHosts")
        if not isinstance(hosts, list) or not hosts or len(hosts) > 7:
            raise ValueError("missing_allowed_hosts")
        if any(hostname("https://" + h) != h for h in hosts):
            raise ValueError("invalid_allowed_host")
        if hostname(row.get("landingPage")) not in hosts:
            raise ValueError("unreviewed_ir_domain")
        if hostname(row.get("evidenceUrl")) not in hosts:
            raise ValueError("unreviewed_source_evidence")
        if not isinstance(row.get("issuer"), str) or not row["issuer"].strip():
            raise ValueError("missing_issuer_name")
        if row.get("documentRetentionApproved") is not False or row.get("publicDocumentDisplayApproved") is not False:
            raise ValueError("unverified_document_permissions")
    return rows


class AnchorParser(HTMLParser):
    """Retain heading context, anchor text and href; ignore scripts and styles."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.heading = ""
        self._heading_tag = None
        self._heading_parts = []
        self._anchor = None
        self._ignore = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._ignore += 1
        if self._ignore:
            return
        if tag in ("h1", "h2", "h3", "h4"):
            self._heading_tag = tag
            self._heading_parts = []
        if tag == "a":
            d = dict(attrs)
            self._anchor = {"href": d.get("href", ""), "text_parts": [], "context": self.heading}

    def handle_data(self, data):
        if self._ignore:
            return
        if self._heading_tag:
            self._heading_parts.append(data)
        if self._anchor:
            self._anchor["text_parts"].append(data)

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._ignore = max(0, self._ignore - 1)
            return
        if tag == self._heading_tag:
            self.heading = " ".join(" ".join(self._heading_parts).split())[:180]
            self._heading_tag = None
        if tag == "a" and self._anchor:
            anchor = self._anchor
            self.links.append({
                "href": anchor["href"],
                "text": " ".join(" ".join(anchor["text_parts"]).split())[:220],
                "context": anchor["context"]
            })
            self._anchor = None


def classify(text, url, context):
    phrase = " ".join((text, context, urlsplit(url).path.rsplit("/", 1)[-1]))
    if re.search(r"\b(esef|xbrl)\b", phrase, re.I):
        return "esef"
    if re.search(r"\b(annual|integrated annual|årsrapport|annual-report)\b", phrase, re.I):
        return "annual_report"
    if re.search(r"\b(quarter|quarterly|interim|half[ -]?year|q[1-4]|kvartal)\b", phrase, re.I):
        return "interim_report"
    if re.search(r"\b(presentation|capital markets|investor day|presentasjon)\b", phrase, re.I):
        return "investor_presentation"
    if re.search(r"\b(sustainability|environmental|esg)\b", phrase, re.I):
        return "sustainability_report"
    return "other_financial_report" if re.search(r"\b(financial|report|results?|resultat)\b", phrase, re.I) else None


def discover(html, issuer):
    """Offline classifier; output is a link review queue, NOT approved/verified reports."""
    if not isinstance(html, str):
        raise ValueError("invalid_html")
    parser = AnchorParser()
    parser.feed(html)
    seen = set()
    output = []
    base = issuer["landingPage"]
    for a in parser.links:
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "javascript:", "data:", "//")):
            continue
        url, _ = urldefrag(urljoin(base, href))
        if hostname(url) not in issuer["allowedHosts"]:
            continue
        path = urlsplit(url).path.lower()
        ext = path.endswith(ALLOWED_FILE_EXTENSIONS)
        phrase = " ".join((a["text"], a["context"], path))
        typ = classify(a["text"], url, a["context"])
        if not typ:
            continue
        # Skip navigation to broad categories and generic unrelated download buttons.
        specific = bool(YEAR_PATTERN.search(phrase) or QUARTER_PATTERN.search(phrase) or
                        re.search(r"\b(report|quarter|financial|esef|xbrl)\b", a["text"], re.I))
        if not (ext or specific):
            continue
        if url in seen:
            continue
        seen.add(url)
        year = YEAR_PATTERN.search(phrase)
        quarter = QUARTER_PATTERN.search(phrase)
        output.append({
            "id": hashlib.sha256((issuer["ticker"] + "|" + url).encode()).hexdigest()[:24],
            "ticker": issuer["ticker"], "issuer": issuer["issuer"],
            "documentUrl": url, "sourcePage": base, "linkText": a["text"],
            "contextHeading": a["context"], "kindCandidate": typ,
            "fiscalYearCandidate": int(year.group(0)) if year else None,
            "quarterCandidate": int(quarter.group(1)) if quarter else None,
            "publishedAt": None, "state": "candidate_requires_review",
            "documentDownloaded": False, "privateRetentionApproved": False,
            "publicDocumentDisplayApproved": False,
            "note": "Source link only: no document contents fetched, rights or fiscal facts inferred."
        })
        if len(output) >= 150:
            break
    return output


def fetch_html(url, hosts):
    """Fetch one original IR landing page, subject to domain, redirect and size constraints."""
    if hostname(url) not in hosts:
        raise ValueError("unapproved_url")
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"})
    with urlopen(req, timeout=18) as response:
        if hostname(response.geturl()) not in hosts:
            raise ValueError("unapproved_redirect")
        kind = response.headers.get_content_type()
        if kind not in ("text/html", "application/xhtml+xml"):
            raise ValueError("not_html")
        raw = response.read(MAX_HTML_BYTES + 1)
        if len(raw) > MAX_HTML_BYTES:
            raise ValueError("html_too_large")
        return raw.decode(response.headers.get_content_charset() or "utf-8", errors="replace")


def robots_permit(page, hosts):
    parts = urlsplit(page)
    robots = parts.scheme + "://" + parts.netloc + "/robots.txt"
    try:
        req = Request(robots, headers={"User-Agent": UA, "Accept": "text/plain"})
        with urlopen(req, timeout=12) as response:
            if hostname(response.geturl()) not in hosts:
                return False
            body = response.read(256_001)
            if len(body) > 256_000:
                return False
            raw = body.decode("utf-8", errors="replace")
    except HTTPError as exc:
        # 404 indicates no robots rules, whereas forbidden/errors require skipping.
        return exc.code in (404, 410)
    except (OSError, ValueError):
        return False
    rp = RobotFileParser()
    rp.parse(raw.splitlines())
    return rp.can_fetch(UA, page)


def merge(previous, found):
    """Preserve older link candidates when an issuer page times out or loses links."""
    items = {}
    for record in previous + found:
        if not isinstance(record, dict):
            continue
        key = record.get("id")
        if isinstance(key, str) and len(key) == 24 and key not in items:
            items[key] = record
    # Current crawl wins for same id, but never creates a rights grant.
    for record in found:
        if record.get("id") in items:
            items[record["id"]] = record
    return sorted(items.values(), key=lambda r: (r.get("ticker", ""), r.get("documentUrl", "")))[:1000]


def run(registry, prior=None, fetch=fetch_html, permit=robots_permit, timestamp=None):
    sources = validate_registry(registry)
    prior = prior or {}
    attempts, discovered = [], []
    for row in sources:
        try:
            if not permit(row["landingPage"], row["allowedHosts"]):
                raise PermissionError("robots_disallowed_or_unavailable")
            links = discover(fetch(row["landingPage"], row["allowedHosts"]), row)
            discovered.extend(links)
            attempts.append({"ticker": row["ticker"], "status": "completed", "candidateLinks": len(links)})
        except (ValueError, OSError, PermissionError) as exc:
            # Intentionally do not expose page content or credentials in error telemetry.
            attempts.append({"ticker": row["ticker"], "status": "failed",
                             "reason": str(exc) if isinstance(exc, (ValueError, PermissionError)) else "network_error"})
    now = timestamp or datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {"schemaVersion": 1, "generated": now, "sourceCount": len(sources),
            "candidateCount": len(merge(prior.get("items", []), discovered)),
            "freshCandidateCount": len(discovered), "attempts": attempts,
            "items": merge(prior.get("items", []), discovered),
            "notice": "Original issuer IR link review queue only. No report bytes downloaded, financial facts parsed, redistribution or archival permissions granted."}


def main():
    ap = argparse.ArgumentParser(description="V101 manual issuer IR link-discovery pilot; no PDF downloads")
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--out", type=Path, default=ROOT / "data/issuer-report-discovery-v101.json")
    ap.add_argument("--network", action="store_true", help="explicit one-shot real website inspection")
    ap.add_argument("--max-sources", type=int, default=4)
    args = ap.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    validate_registry(registry)
    if not args.network:
        print(json.dumps({"reviewedSources": len(registry["sources"]), "notice": "no network requests made; pass --network only in a controlled manual run"}))
        return 0
    if not 1 <= args.max_sources <= MAX_SOURCES:
        ap.error("max-sources exceeds bounded pilot")
    registry["sources"] = registry["sources"][:args.max_sources]
    previous = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() else None
    result = run(registry, previous)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"reviewed": result["sourceCount"], "candidates": result["candidateCount"],
                      "newCandidatesThisRun": result["freshCandidateCount"], "attempts": result["attempts"],
                      "documentBytesSaved": 0}))
    return 0 if any(x["status"] == "completed" for x in result["attempts"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
