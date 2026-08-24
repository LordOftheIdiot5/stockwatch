"""Push fresh signals to Telegram.

The scan cadence is not what makes an alert urgent - the delivery is. A finding
sitting in a JSON file on a page nobody has open is not an alert, however fast
it was computed. This is the part that buzzes a phone.

Needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the environment. Without them
it prints what it would have sent and exits cleanly, so the scan still works for
anyone who has not set it up.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

SIGNALS = Path(__file__).resolve().parent.parent / "data" / "signals.json"
MAX_PER_RUN = 8


def escape(text: str) -> str:
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def compose(alerts: list[dict]) -> str:
    lines = []
    for a in alerts[:MAX_PER_RUN]:
        name = escape(a.get("name") or a["ticker"])
        head = escape(a["headline"])
        if a["kind"] == "price":
            lines.append(f"📈 <b>{name}</b> ({a['ticker']})\n{head}")
        else:
            tag = "⚖️ regulatory" if a.get("regulatory") else "📰"
            lines.append(f"{tag} <b>{name}</b>\n<a href=\"{a['url']}\">{head}</a>")
    if len(alerts) > MAX_PER_RUN:
        lines.append(f"…and {len(alerts) - MAX_PER_RUN} more on the dashboard.")
    return "\n\n".join(lines)


def send(token: str, chat: str, text: str) -> bool:
    payload = urllib.parse.urlencode({
        "chat_id": chat,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=payload), timeout=20) as r:
            return json.loads(r.read()).get("ok", False)
    except Exception as error:                                   # noqa: BLE001
        print(f"  ! telegram: {error}")
        return False


def main() -> int:
    if not SIGNALS.exists():
        print("no signals file; run scan.py first")
        return 0

    data = json.loads(SIGNALS.read_text(encoding="utf-8"))
    fresh = [a for a in data.get("alerts", []) if a.get("fresh")]
    if not fresh:
        print("nothing new to send")
        return 0

    message = compose(fresh)
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set. Would have sent:\n")
        print(message)
        return 0

    print("sent" if send(token, chat, message) else "send failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
