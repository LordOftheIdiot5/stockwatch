"""Observe request-level availability without modifying source parsers.

The metrics describe HTTP transport success, not content validity, data
licensing, quotation timeliness or full source coverage. The scanner continues
working when the telemetry file cannot be written.
"""
from __future__ import annotations
import json
import time
import urllib.parse
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

GROUPS = ('Yahoo prices', 'Oslo NewsWeb', 'MFN filings', 'Google News', 'Finanstilsynet shorts')
_STATS = defaultdict(lambda: {'requests': 0, 'succeeded': 0, 'failed': 0, 'totalMs': 0.0, 'errorTypes': {}})
_INSTALLED = False

def provider(url: str) -> str:
    host = (urllib.parse.urlsplit(url).hostname or '').lower()
    if host.endswith('finance.yahoo.com'): return 'Yahoo prices'
    if host.endswith('oslo.oslobors.no'): return 'Oslo NewsWeb'
    if host == 'mfn.se' or host.endswith('.mfn.se'): return 'MFN filings'
    if host == 'news.google.com': return 'Google News'
    if host.endswith('finanstilsynet.no'): return 'Finanstilsynet shorts'
    return 'Other'

def install(source_module) -> None:
    global _INSTALLED
    if _INSTALLED: return
    original = source_module._get
    def tracked(url: str) -> bytes:
        key = provider(url)
        item = _STATS[key]
        item['requests'] += 1
        start=time.perf_counter()
        try:
            data=original(url)
        except Exception as error:
            item['failed'] += 1
            typ=type(error).__name__
            item['errorTypes'][typ]=item['errorTypes'].get(typ, 0)+1
            raise
        else:
            item['succeeded'] += 1
            return data
        finally:
            item['totalMs'] += max(0.0,(time.perf_counter()-start)*1000)
    source_module._get = tracked
    _INSTALLED = True

def report():
    return {'generated': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'meaning': 'HTTP transport-level requests only; success does not establish that a feed returned usable data.',
            'providers': {k: dict(requests=(_STATS[k]['requests'] if k in _STATS else 0),
                                  succeeded=(_STATS[k]['succeeded'] if k in _STATS else 0),
                                  failed=(_STATS[k]['failed'] if k in _STATS else 0),
                                  avgLatencyMs=round(_STATS[k]['totalMs']/_STATS[k]['requests'], 1) if k in _STATS and _STATS[k]['requests'] else None,
                                  errorTypes=_STATS[k]['errorTypes'] if k in _STATS else {})
                           for k in GROUPS}}

def save(path: Path) -> None:
    path.write_text(json.dumps(report(),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
