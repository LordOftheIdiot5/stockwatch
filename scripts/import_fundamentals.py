"""Import manually verified, source-linked company fundamentals from CSV.

Required columns: ticker, asOf, period, currency, sourceUrl, sourceName.
Optional numeric columns: revenue, netIncome, marketCap, pe, pb, eps,
  dividendPerShare, dividendYield (already in percentage units).

This does NOT auto-scrape or invent numbers. Every row must have a filing or a
provider URL whose license permits this use. Rejects invalid rows rather than
silently publishing them. Example:
  python scripts/import_fundamentals.py ./verified_fundamentals.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'data' / 'fundamentals.json'
REQUIRED = ('ticker', 'asOf', 'period', 'currency', 'sourceUrl', 'sourceName')
METRICS = ('revenue', 'netIncome', 'marketCap', 'pe', 'pb', 'eps', 'dividendPerShare', 'dividendYield')


def parse_row(row: dict, known: set[str]) -> tuple[str, dict]:
    missing = [f for f in REQUIRED if not (row.get(f) or '').strip()]
    if missing:
        raise ValueError('missing ' + ', '.join(missing))
    ticker = row['ticker'].strip()
    if ticker not in known:
        raise ValueError(f'{ticker}: not in watchlist')
    if urlparse(row['sourceUrl']).scheme != 'https' or not urlparse(row['sourceUrl']).netloc:
        raise ValueError('sourceUrl must be HTTPS and contain a hostname')
    if date.fromisoformat(row['asOf']) > date.today():
        raise ValueError('asOf date cannot be in the future')
    metrics = {}
    for key in METRICS:
        raw = (row.get(key) or '').strip()
        if not raw:
            continue
        v = float(raw)
        if not math.isfinite(v):
            raise ValueError(f'{key}: nonfinite number')
        if key in ('pe', 'pb', 'marketCap', 'revenue', 'dividendPerShare', 'dividendYield') and v < 0:
            raise ValueError(f'{key}: negative number requires review')
        metrics[key] = v
    if not metrics:
        raise ValueError('no reported numeric metrics')
    return ticker, {'asOf':row['asOf'], 'period':row['period'].strip(),
                    'currency':row['currency'].strip(), 'sourceUrl':row['sourceUrl'].strip(),
                    'sourceName':row['sourceName'].strip(), 'metrics':metrics}


def main() -> int:
    a=argparse.ArgumentParser()
    a.add_argument('csv_file',type=Path)
    args=a.parse_args()
    known={e['ticker'] for e in json.loads((ROOT/'watchlist.json').read_text(encoding='utf-8'))['tickers']}
    current={'companies':{}}
    if OUT.exists():current=json.loads(OUT.read_text(encoding='utf-8'))
    updated=dict(current.get('companies') or {})
    with args.csv_file.open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        if not set(REQUIRED).issubset(set(reader.fieldnames or [])):
            raise ValueError('CSV missing required column(s): '+', '.join(set(REQUIRED)-set(reader.fieldnames or [])))
        for line,row in enumerate(reader,start=2):
            try:
                ticker,facts=parse_row(row,known)
            except (TypeError,ValueError) as e:
                raise ValueError(f'line {line}: {e}') from e
            updated[ticker]=facts
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({'schemaVersion':1,'companies':updated},indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f'Wrote {len(updated)} source-linked companies to {OUT}')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
