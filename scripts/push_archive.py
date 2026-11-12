"""Optional post-scan D1 ingestion via Cloudflare Worker, configured with GitHub secrets.

STOCKWATCH_ARCHIVE_URL (e.g. https://api.example.com/api/news/ingest)
STOCKWATCH_ARCHIVE_TOKEN (secret). Disabled unless both are explicitly configured.
"""
from __future__ import annotations
import json,os,urllib.request
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    dest=os.getenv('STOCKWATCH_ARCHIVE_URL','').strip()
    token=os.getenv('STOCKWATCH_ARCHIVE_TOKEN','')
    if not dest or not token:
        print('Persistent database push disabled: configure archive URL and token')
        return 0
    if not dest.startswith('https://'):
        raise SystemExit('Only HTTPS archive endpoints allowed')
    archive=json.loads((ROOT/'data/news-archive.json').read_text(encoding='utf-8'))
    cutoff=datetime.now(timezone.utc)-timedelta(days=7)
    items=[]
    for x in archive.get('items',[]):
        try: published=datetime.fromisoformat(x['published'].replace('Z','+00:00'))
        except (KeyError,TypeError,ValueError): continue
        if published>=cutoff: items.append(x)
    for i in range(0,len(items),150):
        batch=items[i:i+150]
        payload=json.dumps({'items':batch},ensure_ascii=False).encode('utf-8')
        req=urllib.request.Request(dest,data=payload,headers={'Content-Type':'application/json','Authorization':'Bearer '+token},method='POST')
        with urllib.request.urlopen(req,timeout=25) as r:
            if r.status!=200:raise RuntimeError('Archive ingestion did not return HTTP 200')
        print(f'Archived {len(batch)} source-linked headlines; token withheld from logs')
    return 0
if __name__=='__main__':raise SystemExit(main())
