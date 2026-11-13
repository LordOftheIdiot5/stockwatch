"""Read-only authentication smoke test for Stockwatch's Cloudflare D1 Worker.

POSTs an empty news batch: it verifies authorization without storing data.
Prints only response status/error category; never prints a bearer token.
"""
import json
import os
import sys
import urllib.error
import urllib.request

from push_archive import clean_token, USER_AGENT

EXPECTED_URL = "https://stockwatch-research-api.gauchovidar.workers.dev/api/news/ingest"

def main():
    url = os.getenv("STOCKWATCH_ARCHIVE_URL", "").strip()
    token = clean_token(os.getenv("STOCKWATCH_ARCHIVE_TOKEN", ""))
    if url != EXPECTED_URL:
        raise SystemExit("Archive endpoint missing or does not match the configured Worker")
    if not token:
        raise SystemExit("Archive token missing in GitHub Actions secrets")
    req = urllib.request.Request(
        url,
        data=b'{"items":[]}',
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token, "User-Agent": USER_AGENT},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.load(response)
            if response.status != 200 or result.get("accepted") != 0:
                raise SystemExit("Unexpected empty-batch ingestion response")
    except urllib.error.HTTPError as exc:
        error_code = "unknown"
        try:
            body = exc.read(2048)
            if b'Error 1010' in body or b'error code: 1010' in body.lower():
                error_code = "cloudflare_browser_integrity_check"
            else:
                error_code = json.loads(body).get("error", "unknown")
        except (ValueError, TypeError):
            pass
        raise SystemExit(f"D1 authentication probe failed: HTTP {exc.code} ({error_code})")
    print("Cloudflare D1 authenticated ingestion probe passed (0 records written)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
