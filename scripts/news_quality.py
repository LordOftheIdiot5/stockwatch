"""Transparent, conservative issuer association and news deduplication.

No LLM guesses and no body scraping. Low-confidence matches remain in the
preserved monthly archive; the default reading view hides them. Source-authorized
issuer codes take precedence over inferred headline text.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from urllib.parse import urlsplit

CATEGORIES = {
    "Earnings / results": r"\b(earnings?|results?|quarterly|q[1-4]|half.year|annual report|interim|resultat|rapport|delars|arseresultat)\b",
    "Dividends": r"\b(dividend|utbytte|utdelning|dividende|ex.dividend|ex.dat[o])\b",
    "M&A": r"\b(acquisitio[n]|acquire[sd]?|merger|takeover|buyout|oppkjop|fusjon|oppk[oø]p|budplikt|bud)\b",
    "Guidance": r"\b(guidance|outlook|profit warning|forecast|prognos|resultatvarsel|nedjuster)\b",
    "Contracts": r"\b(contract|order|tender|awarded|agreement|kontrakt|orderv[aä]rde|avtale)\b",
    "Capital & ownership": r"\b(placement|rights issue|shares issue|capital raise|emisjon|emisjoner|tilbakekj[oø]p|buyback|shareholder|aksjon[aæ]r)\b",
    "Management": r"\b(chief executive|chief financial|appoint|resigns|steps down|ceo|cfo|styreleder|konsernsjef)\b",
}

# Conspicuously ambiguous cross-issuer associations observed on previous scans.
# Never discard a story merely because a competitor is mentioned: downgrade it
# unless the tracked issuer itself is also explicitly present.
DISAMBIGUATION = {
    'SIE.DE': ('siemens energy', 'siemens healthineers'),
    'MTRS.ST': ('mutares',),
    'NOVO-B.CO': ('eli lilly',),
}


def norm(s: str) -> str:
    s = unicodedata.normalize('NFKD', str(s or '').casefold())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('ø', 'o').replace('æ', 'ae').replace('ß', 'ss')
    return ' '.join(re.findall(r'[a-z0-9]+', s))


def has_phrase(haystack: str, needle: str) -> bool:
    a, b = norm(haystack), norm(needle)
    return bool(b and len(b) >= 4 and f' {b} ' in f' {a} ')


def topic(title):
    text = norm(title)
    for label, expression in CATEGORIES.items():
        if re.search(expression, text, re.I):
            return label
    return 'General'


def association(item):
    """'strong', 'mentioned', or 'review': lower tiers are not erased."""
    if item.get('match') == 'issuer_code' and item.get('type') == 'disclosure':
        return 'strong'
    title = item.get('headline') or item.get('english') or ''
    ticker = item.get('ticker') or ''
    name = item.get('name') or ''
    if any(has_phrase(title, v) for v in DISAMBIGUATION.get(ticker, ())):
        # When Siemens Energy is mentioned alongside Siemens, retain the story
        # as an explicitly ambiguous association rather than a confident match.
        return 'review'
    # Avoid matching generic corporate suffixes as issuers.
    if has_phrase(title, name):
        return 'mentioned'
    # Existing scanner matching is a weaker signal than a verifiable phrase.
    return 'review'


def headline_fingerprint(item):
    title = norm(item.get('headline') or item.get('english') or '')
    title = re.sub(r'\b(breaking|update|exclusive|report)\b', '', title).strip()
    return title if len(title) >= 14 else ''


def annotate(items):
    """Annotate without ever inventing a headline, company, or source.

    Duplicate titles for the *same ticker* within a two-day window are marked;
    one is displayed, all underlying records remain in the raw archive.
    """
    out = []
    for item in items:
        x = dict(item)
        x['relevance'] = association(x)
        x['category'] = topic(x.get('headline') or x.get('english') or '')
        x['sourceDomain'] = (urlsplit(x.get('url') or '').hostname or '').lower()
        x['priority'] = 'high' if x['category'] != 'General' and x['relevance'] != 'review' else 'normal'
        x.pop('duplicateOf', None)
        out.append(x)
    # Prefer explicit issuer filings, then named matches, then latest by timestamp.
    def ts(x):
        try:
            return datetime.fromisoformat(str(x.get('published', '')).replace('Z','+00:00')).timestamp()
        except (TypeError, ValueError):
            return 0
    order = sorted(range(len(out)), key=lambda i: (
        {'strong': 2, 'mentioned': 1, 'review': 0}[out[i]['relevance']],
        ts(out[i])), reverse=True)
    chosen = {}
    for idx in order:
        x = out[idx]
        finger = headline_fingerprint(x)
        if not finger:
            continue
        key = (x.get('ticker'), finger)
        earlier = chosen.get(key)
        if earlier and abs(earlier[1] - ts(x)) <= 48 * 3600:
            x['duplicateOf'] = earlier[0]
        else:
            chosen[key] = (x.get('id'), ts(x))
    return out


def summary(items):
    return {'total': len(items),
            'relevant': sum(x.get('relevance') != 'review' and not x.get('duplicateOf') for x in items),
            'review': sum(x.get('relevance') == 'review' for x in items),
            'duplicates': sum(bool(x.get('duplicateOf')) for x in items),
            'issuerLinked': sum(x.get('relevance') == 'strong' for x in items),
            'categories': {k: sum(x.get('category') == k for x in items) for k in [*CATEGORIES,'General']}}
