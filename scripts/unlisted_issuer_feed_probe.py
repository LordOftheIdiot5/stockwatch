"""N41: bounded publisher RSS availability probe, no publication or retention.

Only counts and source health are output. No article text, headlines, raw XML,
article URLs, new scanner schedules, or inferred redistribution permissions.
"""
import argparse
import json
from datetime import datetime, timezone
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
from defusedxml import ElementTree as ET

FEEDS = {
    "neura": "https://neura-robotics.com/feed/",
    "sitegeist": "https://sitegeist-robotics.com/feed/",
    "mistral": "https://mistral.ai/news/rss",
    "lovable": "https://lovable.dev/blog/rss.xml",
}
MAX_BYTES = 2 * 1024 * 1024
MAX_ITEMS = 500

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

def fetch(url):
    if url not in FEEDS.values():
        raise ValueError("Unreviewed endpoint")
    req = Request(url, headers={"User-Agent":"StockwatchResearch/1.0 (+https://stocks.nordl.dev)",
                                "Accept":"application/rss+xml, application/xml, text/xml"})
    with build_opener(NoRedirect()).open(req, timeout=12) as response:
        if response.geturl() != url:
            raise ValueError("Unexpected endpoint")
        raw = response.read(MAX_BYTES + 1)
    return raw

def inspect(raw, url):
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("Invalid feed size")
    root = ET.fromstring(raw, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    channel = root.find("channel") if root.tag == "rss" else None
    if channel is None:
        raise ValueError("Unsupported feed format")
    items = channel.findall("item")
    if len(items) > MAX_ITEMS:
        raise ValueError("Feed item limit exceeded")
    from email.utils import parsedate_to_datetime
    count = 0
    for item in items:
        try:
            link = urlsplit((item.findtext("link") or "").strip())
            date = parsedate_to_datetime(item.findtext("pubDate") or "")
            if (link.scheme == "https" and link.netloc == urlsplit(url).netloc
                    and link.path not in ("", "/") and date.tzinfo is not None):
                count += 1
        except (ValueError, TypeError, OverflowError):
            continue
    return {"status":"rss_observed", "itemCount":len(items), "sameOriginDatedCount":count}

def probe(feed, fetcher=fetch):
    url = FEEDS[feed]
    try:
        return inspect(fetcher(url), url)
    except HTTPError as exc:
        return {"status":"http_error", "httpStatus":exc.code}
    except Exception:
        return {"status":"unconfirmed"}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--feed", choices=tuple(FEEDS), required=True)
    a = p.parse_args()
    result = {"checkedAt":datetime.now(timezone.utc).isoformat(), "feed":a.feed,
              **probe(a.feed), "retentionEnabled":False, "publicationEnabled":False,
              "rightsReview":"pending"}
    print(json.dumps(result))
    return 0 if result["status"] == "rss_observed" else 1

if __name__ == "__main__":
    raise SystemExit(main())
