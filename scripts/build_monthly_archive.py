"""Durable Git-backed monthly article index; strictly additive to the scanner.

GitHub Pages cannot query D1 without a deployed Worker, so month-partitioned JSON
provides on-demand historical lookup from the first enabled scan. Never prunes
months. No article body or copyrighted publisher text is mirrored, only links
and compact attribution metadata collected by Stockwatch.
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone
from build_research_data import dt, collect_news, merge_news
ROOT = Path(__file__).resolve().parents[1]


def build(root=ROOT, now=None):
    now = now or datetime.now(timezone.utc)
    data = root / 'data'
    folder = data / 'news-store'
    folder.mkdir(parents=True, exist_ok=True)
    snapshot = json.loads((data / 'signals.json').read_text(encoding='utf8'))
    prior = json.loads((data / 'news-archive.json').read_text(encoding='utf8')).get('items', []) if (data / 'news-archive.json').exists() else []
    # Include the rolling cache as a one-time backfill; future months are never deleted.
    found = prior + collect_news(snapshot)
    months = defaultdict(list)
    for story in found:
        when = dt(story.get('published'))
        if when and when <= now and story.get('id') and story.get('url','').startswith('https://'):
            months[when.strftime('%Y-%m')].append(story)
    for month, batch in months.items():
        path = folder / (month + '.json')
        existing = json.loads(path.read_text(encoding='utf8')).get('items', []) if path.exists() else []
        # Merge without retention, keeping best available source confidence.
        by_id = {row['id']:row for row in existing if row.get('id')}
        for row in batch:
            old = by_id.get(row['id'])
            if old is None or (old.get('match') == 'unverified' and row.get('match') != 'unverified'):
                by_id[row['id']] = row
        # URL/key attributions can be shared across companies. Preserve unique issuer + id.
        ordered = sorted(by_id.values(), key=lambda x:(x['published'],x['id']), reverse=True)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps({'month':month,'items':ordered},ensure_ascii=False,separators=(',',':'))+'\n', encoding='utf8')
        tmp.replace(path)
    summaries=[]
    for path in sorted(folder.glob('20??-??.json'),reverse=True):
        contents=json.loads(path.read_text(encoding='utf8'))
        items=contents.get('items',[])
        if items:
            summaries.append({'month':path.stem,'count':len(items),'first':items[-1]['published'],'last':items[0]['published']})
    index={'generated':now.isoformat(timespec='seconds'),'total':sum(x['count'] for x in summaries),'months':summaries,
           'storage':'Git-versioned month partitions; Cloudflare D1 search optional'}
    (folder/'index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print('Historical news archive: ',index['total'],'items across',len(summaries),'months')
    return index


if __name__=='__main__':build()
