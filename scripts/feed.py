"""Publish the alerts as an RSS feed.

The open item was getting signals to a phone without sitting on the page. The
options were a Telegram bot, which needs a token, or an email service, which
needs an API key and an account - both of them a dependency and a secret to
look after for something the site is already serving publicly.

A feed needs neither. The data is a static file next to the page, every reader
on every platform speaks RSS, and most of them push. Nothing to authenticate,
nothing to rotate, nothing to break when a key expires.

The one thing that has to be right is the guid. Readers use it to decide what
is new, so it has to be stable for a given story and unique across stories - the
scanner's own alert key is exactly that, and reusing it means a story already
shown is not announced again on the next scan.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
SIGNALS = ROOT / "data" / "signals.json"
OUT = ROOT / "feed.xml"
SITE = "https://stocks.nordl.dev"
MAX_ITEMS = 60

KIND_LABEL = {
    "price": "Price",
    "short": "Short interest",
    "disclosure": "Filing",
    "news": "News",
}


def when(value: str | None, fallback: datetime) -> datetime:
    if not value:
        return fallback
    try:
        parsed = parsedate_to_datetime(value)
    except Exception:                                            # noqa: BLE001
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:                                        # noqa: BLE001
            return fallback
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def cdata(text: str) -> str:
    """Wrap in CDATA, splitting any literal ]]> so it cannot end the section
    early. No headline has ever contained one; a feed that breaks silently on
    the day one does is not worth the saved line."""
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"


def item(alert: dict, generated: datetime) -> str:
    label = KIND_LABEL.get(alert.get("kind", ""), "Signal")
    # The translation leads where there is one, because a reader scanning a
    # feed on a phone should not have to work out what language it is in.
    headline = alert.get("english") or alert["headline"]
    title = f"{alert.get('name') or alert['ticker']} — {headline}"

    body = [f"{label} · {alert['ticker']}"]
    if alert.get("publisher"):
        body.append(alert["publisher"])
    if alert.get("lang") and alert["lang"] != "en":
        body.append(alert["lang"].upper())
    description = " · ".join(body)
    # The original sits under its translation here as it does on the page, so a
    # line can be checked against what was actually written.
    if alert.get("english") and alert["english"] != alert["headline"]:
        description += f"<br><em>{alert['headline']}</em>"
    # CDATA rather than escaping, so the markup above survives. Readers vary in
    # how much HTML they render, and all of them cope with this.
    description = cdata(description)

    return f"""  <item>
   <title>{escape(title)}</title>
   <link>{escape(alert.get('url') or SITE)}</link>
   <guid isPermaLink="false">{escape(alert.get('key') or alert['headline'])}</guid>
   <category>{escape(label)}</category>
   <pubDate>{format_datetime(when(alert.get('published'), generated))}</pubDate>
   <description>{description}</description>
  </item>"""


def build() -> str:
    data = json.loads(SIGNALS.read_text(encoding="utf-8"))
    generated = when(data.get("generated"), datetime.now(timezone.utc))
    alerts = data.get("alerts", [])[:MAX_ITEMS]
    items = "\n".join(item(a, generated) for a in alerts)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
 <channel>
  <title>stockwatch</title>
  <link>{SITE}</link>
  <atom:link href="{SITE}/feed.xml" rel="self" type="application/rss+xml"/>
  <description>Price, volume, regulated filings, short interest and news for {data.get('tickers', 0)} European companies. Not advice.</description>
  <language>en-GB</language>
  <lastBuildDate>{format_datetime(generated)}</lastBuildDate>
  <ttl>60</ttl>
{items}
 </channel>
</rss>
"""


def main() -> int:
    if not SIGNALS.exists():
        print("no signals file; run scan.py first")
        return 0
    OUT.write_text(build(), encoding="utf-8")
    print(f"  wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
