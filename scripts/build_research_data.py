"""Build source-linked Stockwatch research files from the existing scanner output.

Run after scan.py and before the GitHub Actions data commit. No network calls,
no synthetic prices, no invented filings or calendar entries.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
RETENTION_DAYS = 180
MAX_NEWS = 20000

KNOWN_FALSE_MATCHES = {
    'MTRS.ST': (r'\bmutares\b',),
    'SIE.DE': (r'\bsiemens energy\b',),
}


def dt(value):
    if not value: return None
    try:
        x = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        try: x = parsedate_to_datetime(str(value))
        except (TypeError, ValueError, IndexError): return None
    if x.tzinfo is None: x = x.replace(tzinfo=timezone.utc)
    return x.astimezone(timezone.utc)


def iso(value):
    x = dt(value)
    return x.isoformat(timespec='seconds').replace('+00:00','Z') if x else None


def false_match(ticker, headline):
    return any(re.search(pat, str(headline or ''), re.I)
               for pat in KNOWN_FALSE_MATCHES.get(ticker, ()))


def confidence(ticker, name, story):
    issuer = str(story.get('sourceIssuer') or '').strip().upper()
    if issuer and issuer == ticker.split('.')[0].upper() and story.get('kind') == 'disclosure':
        return 'issuer_code'
    cleaned = lambda s: re.sub(r'[^a-z0-9]+', ' ', str(s).casefold()).strip()
    name_text = cleaned(name)
    text = cleaned(story.get('headline') or '')
    if len(name_text) > 4 and (' ' + name_text + ' ') in (' ' + text + ' '):
        return 'name_mentioned'
    return 'unverified'


def collect_news(snapshot):
    companies = {x['ticker']: x for x in snapshot.get('companies', [])}
    items = []
    for company in companies.values():
        for story in company.get('stories') or []:
            items.append((company['ticker'], company.get('name',''), story))
    for alert in snapshot.get('alerts') or []:
        if alert.get('kind') in {'news','disclosure'}:
            c = companies.get(alert.get('ticker'), {})
            items.append((alert.get('ticker',''), c.get('name',alert.get('name','')), alert))
    out = []
    for ticker,name,story in items:
        if story.get('kind') not in {'news','disclosure'} or not ticker: continue
        title=story.get('headline') or ''
        if false_match(ticker,title): continue
        link=str(story.get('url') or '')
        if not link.startswith('https://'): continue
        date=iso(story.get('published')) or iso(snapshot.get('generated'))
        if not date: continue
        key=str(story.get('key') or f'{ticker}:{link}')
        out.append(dict(id=key,ticker=ticker,name=name,sector=companies.get(ticker,{}).get('sector',''),
                        type=story['kind'],headline=title,english=story.get('english'),
                        publisher=story.get('publisher') or '',url=link,published=date,
                        lang=story.get('lang') or '',regulatory=story.get('regulatory') is True,
                        match=confidence(ticker,name,story)))
    return out


def merge_news(previous, found, now):
    cutoff = now-timedelta(days=RETENTION_DAYS)
    merged = {x['id']: x for x in previous if x.get('id') and dt(x.get('published')) and dt(x['published'])>=cutoff}
    for item in found:
        x=dt(item.get('published'))
        if x and x>=cutoff and x<=now+timedelta(days=1):
            # An old record can be refined by a better source match later.
            prior=merged.get(item['id'])
            if not prior or (prior.get('match') == 'unverified' and item['match'] != 'unverified'):
                merged[item['id']]=item
    return sorted(merged.values(),key=lambda x:x['published'],reverse=True)[:MAX_NEWS]


def extract_events(news, now):
    """Conservative calendar: dates explicitly printed in dated filing headlines.

    Events are PROVISIONAL until separately checked against the original filing;
    no guessing ex-dates, payment dates, dividend amounts, or quarter dates.
    """
    events=[]
    date_pat=r'\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b'
    for s in news:
        if s.get('type')!='disclosure': continue
        title=s.get('headline') or ''
        low=title.casefold()
        if not re.search(r'\b(results|earnings|financial report|quarterly report|interim report|resultatrapport)\b',low):continue
        if not re.search(r'\b(on|for|scheduled|publishes|publication|announce[s]?|present[s]?)\b',low):continue
        matches=re.findall(date_pat,title)
        if len(matches)!=1: continue
        day,mon,year=map(int,matches[0])
        try: event_date=datetime(year,mon,day,tzinfo=timezone.utc)
        except ValueError: continue
        if event_date.date()<now.date() or event_date>now+timedelta(days=390):continue
        events.append(dict(id=f'{s["ticker"]}:earnings:{event_date.date()}',ticker=s['ticker'],
                           name=s['name'],sector=s['sector'],type='earnings',date=str(event_date.date()),
                           label='Results announcement',sourceUrl=s['url'],sourceTitle=title,
                           verification='provisional',extractedFrom='disclosure headline'))
    return events


def _provider_status(transport):
    keys=('Yahoo prices','Oslo NewsWeb','MFN filings','Google News','Finanstilsynet shorts')
    providers=(transport or {}).get('providers',{})
    result={}
    for key in keys:
        d=providers.get(key)
        if not d: result[key]='not_instrumented'; continue
        total=int(d.get('requests') or 0)
        ok=int(d.get('succeeded') or 0)
        failed=int(d.get('failed') or 0)
        result[key]='not_observed' if total==0 else 'requests_ok' if failed==0 else 'request_errors' if ok else 'requests_failed'
    return result


def build_health(snapshot,watchlist,context,now, transport=None):
    quotes={x['ticker']:x for x in snapshot.get('companies',[]) if x.get('close') is not None}
    universe=watchlist.get('tickers',[])
    exchange=Counter((x.get('exchange') or 'Unknown') for x in universe)
    coverage=Counter((x.get('exchange') or 'Unknown') for x in universe if x['ticker'] in quotes)
    source_age=lambda s: round((now-dt(s)).total_seconds()/3600,2) if dt(s) else None
    exchanges=[dict(name=x,total=exchange[x],priced=coverage[x],missing=exchange[x]-coverage[x])
               for x in sorted(exchange)]
    return dict(generated=iso(now),latestScan=snapshot.get('generated'),
                scanAgeHours=source_age(snapshot.get('generated')),
                contextAgeHours=source_age(context.get('generated')),
                tracked=len(universe),priced=len(quotes),missing=[dict(ticker=x['ticker'],name=x.get('name',''),exchange=x.get('exchange','')) for x in universe if x['ticker'] not in quotes],
                exchanges=exchanges,storedStories=sum(len(x.get('stories') or []) for x in snapshot.get('companies',[])),
                caveat='Provider status covers HTTP request success/failure during the latest scan, not parsed data quality or guaranteed timeliness.',
                sourceStatus=_provider_status(transport),
                sourceRequests=(transport or {}).get('providers',{}))


def build(root=ROOT, now=None):
    now=now or datetime.now(timezone.utc)
    folder=root/'data'
    snapshot=json.loads((folder/'signals.json').read_text(encoding='utf-8'))
    watchlist=json.loads((root/'watchlist.json').read_text(encoding='utf-8'))
    context=json.loads((folder/'context.json').read_text(encoding='utf-8')) if (folder/'context.json').exists() else {}
    old_path=folder/'news-archive.json'
    prev=json.loads(old_path.read_text(encoding='utf-8')).get('items',[]) if old_path.exists() else []
    news=merge_news(prev,collect_news(snapshot),now)
    archive=dict(generated=iso(now),items=news,retentionDays=RETENTION_DAYS)
    events=extract_events(news,now)
    # Allow curated, source-linked entries; never overwrite or fabricate them.
    manual_path=folder/'events-manual.json'
    if manual_path.exists():
        manual=json.loads(manual_path.read_text(encoding='utf-8')).get('items',[])
        for event in manual:
            if event.get('ticker') and event.get('date') and str(event.get('sourceUrl','')).startswith('https://'):
                if str(event['date'])>=str(now.date()): events.append(event)
    events=list({x['id']:x for x in events if x.get('id')}.values())
    events.sort(key=lambda x:(x['date'],x['name']))
    transport_path=folder/'request-health.json'
    transport=json.loads(transport_path.read_text(encoding='utf-8')) if transport_path.exists() else None
    health=build_health(snapshot,watchlist,context,now,transport)
    for file,payload in [('news-archive.json',archive),('events.json',dict(generated=iso(now),items=events)),('source-health.json',health)]:
        (folder/file).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Archive: {len(news)} stories | Calendar: {len(events)} sourced events | Health: {health["priced"]}/{health["tracked"]} prices')

if __name__=='__main__':build()
