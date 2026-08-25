"""Translate headlines into English, once each, and remember the result.

Two reasons this exists, and the second is the important one.

The obvious reason is reading: a German or Finnish headline is no use to someone
who does not read German or Finnish.

The real reason is matching. The same event is reported in every market at once
- one Aker BP gas find appeared in all ten language feeds - and the headline
comparison in scan.py can only see through a language boundary when the words
happen to be cognates. It could tell "Vaar Energi" from "Var Energi" but not
"Q2 results beat expectations" from "kvartalsresultat over forventningene".
Translating first turns cross-language deduplication into ordinary same-language
deduplication, which already works.

Three providers, used in whatever order is configured:

  DeepL       the best prose of the three for European languages. 500,000
              characters a month free, which is close to this workload rather
              than comfortably above it.       DEEPL_API_KEY
  Azure       2,000,000 characters a month free, much the largest allowance.
              AZURE_TRANSLATOR_KEY, plus AZURE_TRANSLATOR_REGION when the
              resource is regional rather than global.
  MyMemory    no key and no signup, in exchange for roughly forty headlines an
              hour. This is what runs when nothing else is set, and it works -
              it is only slow to warm up.      MYMEMORY_EMAIL raises it tenfold

Both keyed providers accept batches, which matters more than it looks: a cold
start is over a thousand headlines, and batching makes that twenty requests
rather than a thousand.

The cache is the point rather than an optimisation whichever provider is in
use - a headline seen at 09:00 must not be bought again at 10:00 - and it is
committed with the results, because the runner is thrown away between scans.
"""
from __future__ import annotations

import html
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

CACHE_PATH = Path(__file__).resolve().parent.parent / "data" / "translations.json"

MAX_CHARS = 480          # headlines are never longer, and MyMemory rejects them
UA = "stockwatch/1.0 (+https://nordl.dev)"

# Languages read directly, so no translation is bought for them.
READABLE = {"en", "no", "nb", "nn", "sv", "da", "es"}


def clean(raw: str) -> str:
    """Tidy one translation.

    Services return HTML-escaped text, so an apostrophe comes back as &#39;.
    The page escapes again on the way out, so without this a reader sees the
    entity itself: "Now they don&#39;t call".
    """
    return html.unescape(raw or "").strip()


def _post(url: str, data: bytes, headers: dict) -> dict | list | None:
    request = urllib.request.Request(url, data=data,
                                     headers={"User-Agent": UA, **headers})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except Exception:                                            # noqa: BLE001
        return None


class DeepL:
    """Free-tier keys end in ':fx' and use a different host from paid ones."""

    name = "deepl"
    batch = 40
    per_run = 600

    def __init__(self, key: str) -> None:
        self.key = key
        self.host = ("https://api-free.deepl.com" if key.endswith(":fx")
                     else "https://api.deepl.com")

    def translate(self, texts: list[str], lang: str) -> list[str | None]:
        body = [("target_lang", "EN-GB")]
        # DeepL detects the source well, so naming it only helps where the
        # code is one it knows. Norwegian is "NB" to DeepL, not "NO".
        known = {"de", "fr", "nl", "it", "pt", "pl", "fi", "sv", "da", "es"}
        if lang in known:
            body.append(("source_lang", lang.upper()))
        elif lang == "no":
            body.append(("source_lang", "NB"))
        body.extend(("text", t) for t in texts)
        payload = _post(f"{self.host}/v2/translate",
                        urllib.parse.urlencode(body).encode(),
                        {"Authorization": f"DeepL-Auth-Key {self.key}",
                         "Content-Type": "application/x-www-form-urlencoded"})
        if not isinstance(payload, dict):
            return [None] * len(texts)
        out = [clean(t.get("text", "")) for t in payload.get("translations", [])]
        # A short reply cannot be paired back to its inputs, so treat the whole
        # batch as unavailable rather than risk attaching the wrong text.
        return out if len(out) == len(texts) else [None] * len(texts)


class Azure:
    """Azure AI Translator. The F0 tier is two million characters a month."""

    name = "azure"
    batch = 40
    per_run = 900

    def __init__(self, key: str, region: str = "") -> None:
        self.key = key
        self.region = region

    def translate(self, texts: list[str], lang: str) -> list[str | None]:
        url = ("https://api.cognitive.microsofttranslator.com/translate"
               "?api-version=3.0&to=en")
        if lang and lang != "en":
            url += f"&from={'nb' if lang == 'no' else lang}"
        headers = {"Ocp-Apim-Subscription-Key": self.key,
                   "Content-Type": "application/json; charset=UTF-8"}
        if self.region:
            headers["Ocp-Apim-Subscription-Region"] = self.region
        payload = _post(url, json.dumps([{"Text": t} for t in texts]).encode("utf-8"),
                        headers)
        if not isinstance(payload, list) or len(payload) != len(texts):
            return [None] * len(texts)
        return [clean((item.get("translations") or [{}])[0].get("text", "")) or None
                for item in payload]


class MyMemory:
    """No key and no signup, in exchange for a small daily allowance.

    Roughly 5000 words a day shared across every scan, so one run gets about
    forty headlines. Whatever is not translated this hour is translated next
    hour; nothing is lost, it arrives in English later.
    """

    name = "mymemory"
    batch = 1
    per_run = 40

    def __init__(self, email: str = "") -> None:
        self.email = email
        if email:
            self.per_run = 380          # an address raises the allowance tenfold

    def translate(self, texts: list[str], lang: str) -> list[str | None]:
        text = texts[0]
        url = ("https://api.mymemory.translated.net/get?q="
               + urllib.parse.quote(text) + f"&langpair={lang}|en")
        if self.email:
            url += "&de=" + urllib.parse.quote(self.email)
        try:
            request = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read())
        except Exception:                                        # noqa: BLE001
            return [None]
        out = clean((payload.get("responseData") or {}).get("translatedText") or "")
        # A spent quota comes back as prose in the translation field, so a 200
        # is not on its own a success.
        if not out or payload.get("responseStatus") not in (200, "200") \
                or "MYMEMORY WARNING" in out.upper():
            return [None]
        return [out]


def providers() -> list:
    """Whatever is configured, best first. MyMemory is always last, and always
    present, so a scan with no keys at all still translates something."""
    found = []
    key = os.environ.get("DEEPL_API_KEY", "").strip()
    if key:
        found.append(DeepL(key))
    key = os.environ.get("AZURE_TRANSLATOR_KEY", "").strip()
    if key:
        found.append(Azure(key, os.environ.get("AZURE_TRANSLATOR_REGION", "").strip()))
    found.append(MyMemory(os.environ.get("MYMEMORY_EMAIL", "").strip()))
    return found


class Translator:
    def __init__(self) -> None:
        self.cache: dict[str, str] = {}
        if CACHE_PATH.exists():
            try:
                self.cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            except Exception:                                    # noqa: BLE001
                self.cache = {}
        self.providers = providers()
        self.spent = {p.name: 0 for p in self.providers}
        self.hits = 0
        self.bought = 0
        self.failures = 0

    @staticmethod
    def key(text: str, lang: str) -> str:
        return f"{lang}:{text}"

    def warm(self, wanted: list[tuple[str, str]]) -> None:
        """Translate everything worth translating, in batches, before the scan
        needs any of it.

        Gathering first rather than translating lazily inside the loop is what
        lets the keyed providers batch at all, and it also means the scan never
        stalls halfway through a company waiting on a slow service.
        """
        by_lang: dict[str, list[str]] = {}
        queued: set[str] = set()
        for text, lang in wanted:
            if lang in ("en", "en-GB", "en-US") or not text.strip():
                continue
            if len(text) > MAX_CHARS:
                continue
            cache_key = self.key(text, lang)
            if cache_key in self.cache or cache_key in queued:
                continue
            queued.add(cache_key)
            by_lang.setdefault(lang, []).append(text)

        for provider in self.providers:
            for lang, texts in by_lang.items():
                pending = [t for t in texts if self.key(t, lang) not in self.cache]
                for start in range(0, len(pending), provider.batch):
                    if self.spent[provider.name] >= provider.per_run:
                        break
                    chunk = pending[start:start + provider.batch]
                    results = provider.translate(chunk, lang)
                    got = 0
                    for text, result in zip(chunk, results):
                        if result:
                            self.cache[self.key(text, lang)] = result
                            got += 1
                        else:
                            self.failures += 1
                    self.spent[provider.name] += len(chunk)
                    self.bought += got
                    # A whole batch failing means this provider is done for now
                    # - spent quota, bad key, an outage - so stop asking it and
                    # let the next one pick up the rest.
                    if got == 0:
                        self.spent[provider.name] = provider.per_run
                        break

    def english(self, text: str, lang: str) -> str | None:
        """English for a headline, or None if it is not available yet.

        Reads only what warm() has already collected; nothing is bought here.
        """
        if lang in ("en", "en-GB", "en-US"):
            return text
        got = self.cache.get(self.key(text, lang))
        if got is not None:
            self.hits += 1
        return got

    def save(self) -> None:
        CACHE_PATH.parent.mkdir(exist_ok=True)
        CACHE_PATH.write_text(
            json.dumps(self.cache, ensure_ascii=False, indent=0, sort_keys=True),
            encoding="utf-8")

    def report(self) -> str:
        used = ", ".join(f"{name} {n}" for name, n in self.spent.items() if n)
        return (f"translations: {self.hits} read, {self.bought} bought, "
                f"{self.failures} unavailable, {len(self.cache)} held"
                + (f" [{used}]" if used else ""))
