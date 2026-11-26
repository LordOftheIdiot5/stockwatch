# N41 — Publisher news feed pilot (26 November 2026)

The first production unlisted-company Google News scan returned HTTP 503 for all eight queries. Independently inspected four publisher-operated RSS endpoints, each returning recognizable RSS with dated items and original links:

| Company | Source | Status |
|---|---|---|
| NEURA Robotics | https://neura-robotics.com/feed/ | RSS observed |
| Sitegeist | https://sitegeist-robotics.com/feed/ | RSS observed |
| Mistral AI | https://mistral.ai/news/rss | RSS observed |
| Lovable | https://lovable.dev/blog/rss.xml | RSS observed |
| ANYbotics | https://www.anybotics.com/feed/ | Timeout, unconfirmed |

Publisher feeds are independent of Google News, but may include articles about third parties or coverage summaries; issuer-hosted does not mean every statement is independently verified. Public availability alone does not establish permission to retain/re-publish an automated news database. No rights approval inferred.

Run a single private metadata-only probe:

    python -m pip install defusedxml==0.7.1
    python scripts/unlisted_issuer_feed_probe.py --feed neura

Other feed IDs: sitegeist, mistral, lovable. Only counts and status printed; no article title, URL, body, XML, or raw bytes stored. Fixed endpoints, bounded response and XML parser, no redirects/retries. No recurring workflow or public projection added. Unit tests: python -m unittest discover -s tests -p test_unlisted_issuer_feed_probe.py -v .

Next: review collection/retention/display permissions per provider, document permitted cadence, confirm actual feed health from production runner, then implement a separate rights-gated source-linked news projection (no full-text copy). Prefer original dated announcements, identify third-party references separately, deduplicate against reviewed summaries by exact original URL, and preserve last-known authorized records through outages. Existing master N41 remains authoritative. This probe is not a substitute for production automatic news coverage.
