"""Idempotent authenticated metadata upload to the optional D1 Worker.

Normal mode uploads a rolling seven days. After provisioning a new database,
run python scripts/push_archive.py --backfill to upload all Git-backed months.
Never sends article bodies or prints an authentication token.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_PAYLOAD_BYTES = 440_000
MAX_ITEMS_PER_BATCH = 100

def _published(item):
    try:
        value = datetime.fromisoformat(str(item['published']).replace('Z', '+00:00'))
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError, OverflowError):
        return None

def load_items(root=ROOT, *, backfill=False, now=None):
    now = now or datetime.now(timezone.utc)
    if backfill:
        paths = sorted((root / 'data' / 'news-store').glob('20??-??.json'))
        if not paths:
            raise FileNotFoundError('No monthly archive available for backfill')
    else:
        paths = [root / 'data' / 'news-archive.json']
    records = {}
    for path in paths:
        data = json.loads(path.read_text(encoding='utf8'))
        for item in data.get('items', []):
            when = _published(item)
            if not when or when > now + timedelta(days=1):
                continue
            if not backfill and when < now - timedelta(days=7):
                continue
            if not item.get('id') or not str(item.get('url', '')).startswith('https://'):
                continue
            records[item['id']] = item
    return sorted(records.values(), key=lambda x: (x['published'], x['id']))

def pack_batches(items, *, max_bytes=MAX_PAYLOAD_BYTES):
    batch = []
    for item in items:
        trial = batch + [item]
        serialized = json.dumps({'items': trial}, ensure_ascii=False, separators=(',', ':')).encode('utf8')
        if len(serialized) > max_bytes or len(trial) > MAX_ITEMS_PER_BATCH:
            if not batch:
                raise ValueError('One article exceeds the ingestion payload limit')
            yield batch
            batch = [item]
            check = json.dumps({'items': batch}, ensure_ascii=False, separators=(',', ':')).encode('utf8')
            if len(check) > max_bytes:
                raise ValueError('One article exceeds the ingestion payload limit')
        else:
            batch = trial
    if batch:
        yield batch

def clean_token(value):
    """Trim Windows PowerShell BOM artifacts; never log or echo the secret."""
    token = (value or '').lstrip('\ufeff').strip()
    if token and not re.fullmatch(r'[0-9a-fA-F]{64}', token):
        raise ValueError('Invalid archive token encoding: rotate with deploy/repair-archive-secret.ps1')
    return token


def main(argv=None, root=ROOT):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--backfill', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)
    dest = os.getenv('STOCKWATCH_ARCHIVE_URL', '').strip()
    token = clean_token(os.getenv('STOCKWATCH_ARCHIVE_TOKEN', ''))
    if not args.dry_run and (not dest or not token):
        print('D1 archive push disabled: URL/token not configured; Git archive remains available')
        return 0
    if dest and (not dest.startswith('https://') or not dest.endswith('/api/news/ingest')):
        raise SystemExit('Archive endpoint must be an HTTPS /api/news/ingest URL')
    items = load_items(root, backfill=args.backfill)
    total = 0
    for batch in pack_batches(items):
        if not args.dry_run:
            payload = json.dumps({'items': batch}, ensure_ascii=False, separators=(',', ':')).encode('utf8')
            request = urllib.request.Request(dest,data=payload,headers={
                'Content-Type':'application/json','Authorization':'Bearer '+token},method='POST')
            with urllib.request.urlopen(request,timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(f'Database ingestion returned HTTP {response.status}')
                result = json.loads(response.read())
                if result.get('accepted') != len(batch):
                    raise RuntimeError('Database ingestion did not acknowledge the full batch')
        total += len(batch)
    print(f'{"Validated" if args.dry_run else "Uploaded"} {total} unique news records'
          + (' (full backfill)' if args.backfill else ' (rolling 7 days)'))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
