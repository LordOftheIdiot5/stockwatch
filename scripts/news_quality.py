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
from news_drivers import classify, VERSION

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


# Brand names and short acronyms can name a product, a sporting event,
# a generic term or an entirely different organization. They are never proof
# of an issuer relationship by themselves. These rules affect attribution,
# not historical retention or the original source URL.
ISSUER_CONTEXT = {
    # Spanish rail manufacturer CAF vs Confederation of African Football.
    'CAF.MC': (
        r'\b(?:construcciones y auxiliar(?:es)? de ferrocarriles|caf (?:s\s*a\s*u?|rail(?:way)?s?|railcars?|rolling stock|trains?|tramways?|metros?|shares?|stock|earnings|results|revenue|orders?|contract(?:s)?|awards?))\b',
        'short-acronym CAF lacks rail/issuer context',
    ),
    # Frontline plc vs the everyday adjective/noun "frontline".
    'FRO.OL': (
        r'\b(?:frontline (?:plc|ltd|limited|tanker|shipping|shares?|stock|earnings|results|dividend|fleet|vessels?|freight|rates|charter)|fro (?:shares?|stock)|(?:tanker|shipping company) frontline)\b',
        'common word Frontline lacks shipping/issuer context',
    ),
    # Ferrari NV vs a car, race, racing series, or individual.
    'RACE.MI': (
        r'\b(?:ferrari (?:n\s*v|shares?|stock|earnings|results|revenue|profit|forecast|guidance|orders?|deliveries|quarterly|annual|company|group|investors?|buyback|dividend|ceo|cfo)|race mi|(?:shares?|stock|earnings|revenue|profits?|guidance) (?:of |for )?ferrari)\b',
        'Ferrari brand/sport mention lacks issuer-financial context',
    ),
    # Airbus SE vs aircraft-type mentions without the manufacturer's action.
    'AIR.PA': (
        r'\b(?:airbus (?:s\s*e|shares?|stock|earnings|results|revenue|profit|guidance|orders?|deliver(?:s|ed|ies)?|signs?|signed|wins?|won|builds?|manufactur(?:e|es|ed)|announc(?:es|ed)|company|group|ceo|cfo|investors?|contract(?:s)?)|(?:shares?|stock|earnings|revenue|profits?|guidance) (?:of |for )?airbus)\b',
        'Airbus aircraft/product mention lacks issuer action',
    ),
}


def identity_evidence(item):
    """Return issuer-evidence tier and a reviewable reason; never guess bodies."""
    if item.get('match') == 'issuer_code' and item.get('type') == 'disclosure':
        return 'strong', 'source-provided issuer code on disclosure'
    title = (item.get('headline') or '') + ' ' + (item.get('english') or '')
    ticker = str(item.get('ticker') or '')
    name = str(item.get('name') or '')
    normalized = norm(title)
    # Explicit competitor references are not verified issuer evidence.
    if any(has_phrase(title, v) for v in DISAMBIGUATION.get(ticker, ())):
        return 'review', 'possible competitor or cross-issuer mention'
    if ticker in ISSUER_CONTEXT:
        pattern, reason = ISSUER_CONTEXT[ticker]
        if not re.search(pattern, normalized):
            return 'review', reason
    if ticker in ('P911.DE', 'PAH3.DE'):
        legal = r'\bporsche ag\b' if ticker == 'P911.DE' else r'\bporsche (?:se|automobil holding)\b'
        if not re.search(legal, normalized):
            return 'review', 'Porsche brand mention lacks correct legal issuer'
    if has_phrase(title, name):
        return 'mentioned', 'named headline reference only; not issuer-confirmed'
    return 'review', 'no issuer-specific headline reference'


def association(item):
    """'strong', 'mentioned', or 'review'—retain the review-tier source record."""
    return identity_evidence(item)[0]


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
        x['relevance'], x['identityReviewReason'] = identity_evidence(x)
        x['identityTier'] = ('issuer_verified' if x['relevance']=='strong' else
                             'named_reference' if x['relevance']=='mentioned' else 'review_candidate')
        x['category'] = topic(x.get('headline') or x.get('english') or '')
        x['driverVersion'] = VERSION
        x['driverTags'] = classify(x,norm(x.get('headline') or x.get('english') or ''))
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
        # Distinct SEC accession numbers are distinct filings, even when form titles match.
        finger = ('sec:'+str(x['sourceAccession'])) if x.get('sourceFeed')=='sec_edgar' and x.get('sourceAccession') else headline_fingerprint(x)
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
            'namedReferences':sum(x.get('relevance') == 'mentioned' for x in items),
            'withheldFromIssuerEvents':sum(x.get('relevance') == 'review' for x in items),
            'identityTiers': {tier:sum(x.get('identityTier') == tier for x in items) for tier in ('issuer_verified','named_reference','review_candidate')},
            'driverClassification': {'version':VERSION,
                'classified':sum(bool(x.get('driverTags')) and not x.get('duplicateOf') for x in items),
                'categories':{k:sum(not x.get('duplicateOf') and any(t['driver']==k for t in x.get('driverTags',[])) for x in items) for k in ('numbers','prices','operations','potential','risk')},
                'notice':'Multi-label topical association; not sentiment, price effect or verified headline facts.'},
            'categories': {k: sum(x.get('category') == k for x in items) for k in [*CATEGORIES,'General']}}
