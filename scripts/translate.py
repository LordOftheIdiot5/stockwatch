"""Translate headlines into English, once each, and remember the result.

Two reasons this exists, and the second is the important one.

The obvious reason is reading: a German or Finnish headline is no use to someone
who does not read German or Finnish.

The real reason is matching. The same event is reported in every market at once
- one Aker BP gas find appeared in all ten language feeds - and the headline
comparison in scan.py can only see through a language boundary when the words
happen to be cognates. It could tell "Vår Energi" from "Vaar Energi" but not
"Q2 results beat expectations" from "kvartalsresultat over forventningene".
Translating first turns cross-language deduplication into ordinary same-language
deduplication, which already works.

MyMemory is used because it is free, needs no key, and returns usable prose.
It is also word-capped per day, which is why the cache is the point rather than
an optimisation: a headline seen at 09:00 must not be paid for again at 10:00.
The cache is committed with the results, so it survives the runner being thrown
away between scans.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "translations.json"

# The anonymous tier is roughly 5000 words a day and every scan shares it, so a
# single run may not spend it all. Whatever is not translated this hour is
# translated next hour; nothing is lost, it just arrives in English later.
MAX_PER_RUN = 140
MAX_CHARS = 480          # MyMemory rejects longer, and headlines never are

# Languages read directly, so no translation is bought for them.
READABLE = {"en", "no", "nb", "nn", "sv", "da", "es"}


class Translator:
    def __init__(self) -> None:
        self.cache: dict[str, str] = {}
        if CACHE_PATH.exists():
            try:
                self.cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            except Exception:                                    # noqa: BLE001
                self.cache = {}
        self.spent = 0
        self.hits = 0
        self.misses = 0
        self.failures = 0
        # An address raises the daily allowance; without one the anonymous tier
        # applies. Set MYMEMORY_EMAIL as a repository secret to use it.
        self.email = os.environ.get("MYMEMORY_EMAIL", "").strip()

    @staticmethod
    def key(text: str, lang: str) -> str:
        return f"{lang}:{text}"

    def english(self, text: str, lang: str) -> str | None:
        """English for a headline, or None if it could not be bought today.

        Returns the text unchanged when it is already English.
        """
        if lang in ("en", "en-GB", "en-US"):
            return text
        cached = self.cache.get(self.key(text, lang))
        if cached is not None:
            self.hits += 1
            return cached
        if self.spent >= MAX_PER_RUN or len(text) > MAX_CHARS or not text.strip():
            return None

        url = ("https://api.mymemory.translated.net/get?q="
               + urllib.parse.quote(text) + f"&langpair={lang}|en")
        if self.email:
            url += "&de=" + urllib.parse.quote(self.email)
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "stockwatch/1.0 (+https://nordl.dev)"})
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read())
        except Exception:                                        # noqa: BLE001
            self.failures += 1
            return None

        out = ((payload.get("responseData") or {}).get("translatedText") or "").strip()
        status = payload.get("responseStatus")
        # A quota message comes back as prose in the translation field, so a
        # 200 is not on its own a success.
        if not out or status not in (200, "200") or "MYMEMORY WARNING" in out.upper():
            self.failures += 1
            return None

        self.spent += 1
        self.misses += 1
        self.cache[self.key(text, lang)] = out
        return out

    def save(self) -> None:
        CACHE_PATH.parent.mkdir(exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps(self.cache, ensure_ascii=False, indent=0, sort_keys=True),
            encoding="utf-8")

    def report(self) -> str:
        return (f"translations: {self.hits} cached, {self.misses} bought, "
                f"{self.failures} unavailable, {len(self.cache)} held")
