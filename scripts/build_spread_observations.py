"""Append independently calculated A/B *indicator* snapshots from scanner output.

Unlike historical share prices this data contains no third-party OHLCV bars. It
records the ratio already published by Stockwatch on a particular UTC scan day.
It is not a reconstructed 1Y price series, tradeable quote, or an assurance of
rights to redistribute any underlying market data. Licence review is still
required before commercial resale of these observations.
"""
from __future__ import annotations
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

MAX_DAYS = 730


def valid_day(value):
    try:
        day = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if day.tzinfo is None: return None
        return day.astimezone(timezone.utc).date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return None


def build(root: Path, now: datetime | None = None):
    now = now or datetime.now(timezone.utc)
    location = root / 'data' / 'spread-observations.json'
    context_file = root / 'data' / 'context.json'
    if not context_file.exists(): return {}
    data = json.loads(context_file.read_text(encoding='utf-8'))
    day = valid_day(data.get('generated'))
    if not day or day > now.date().isoformat(): return {}
    if (now.date() - datetime.fromisoformat(day).date()).days > 7: return {}
    try: history = json.loads(location.read_text(encoding='utf-8'))
    except (OSError, ValueError): history = {}
    pairs = history.get('pairs', {})
    cutoff = (now - timedelta(days=MAX_DAYS)).date().isoformat()
    for p in data.get('shareClasses') or []:
        a, b = p.get('a'), p.get('b')
        value = p.get('ratio')
        if not a or not b or type(value) not in (int, float) or not math.isfinite(value) or value <= 0: continue
        key = f'{a}/{b}'
        older = pairs.get(key, [])
        # Source scanner may run hourly; retain one point per UTC day and
        # replace the day with its latest observed ratio.
        by_day = {x['date']:x for x in older if isinstance(x,dict)
                  and cutoff <= str(x.get('date','')) <= day
                  and type(x.get('value')) in (int,float) and math.isfinite(x['value']) and x['value'] > 0}
        by_day[day] = {'date': day, 'value': round(value, 6)}
        pairs[key] = [by_day[k] for k in sorted(by_day)]
    result = {'generated': data.get('generated'),
              'method': 'Dated snapshots of Stockwatch calculated A/B ratios; NOT reconstructed historical share prices.',
              'frequency': 'one UTC observation per day',
              'source': 'Stockwatch scanner context',
              'redistributionNotice': 'Derived observations; third-party commercial redistribution rights must be reviewed separately.',
              'pairs': pairs}
    location.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


if __name__ == '__main__':
    build(Path(__file__).resolve().parents[1])
