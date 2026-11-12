"""Import licensed daily price and freight history; never scrape or invent figures.

Input is a UTF-8 CSV with date,close,volume (equity) or date,value (freight)
plus an explicit JSON entitlement manifest supplied by the data owner/provider.
The manifest MUST grant public redistribution for stockwatch; private analytics
rights are insufficient. Imported data retains source, rights and fetch date.
"""
from __future__ import annotations
import argparse,csv,json,math,re
from datetime import date,datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def valid_manifest(m, asset):
    if m.get('assetType') != asset or m.get('redistributionPermitted') is not True:
        raise ValueError('Manifest must explicitly authorize public redistribution for this asset type')
    if not all(isinstance(m.get(k),str) and m[k].strip() for k in ('provider','licenseReference','sourceUrl')):
        raise ValueError('Missing provider, license reference, or source URL')
    if not m['sourceUrl'].startswith('https://') or not m['licenseReference'].startswith('https://'):
        raise ValueError('Source and license references must be HTTPS')
    if asset == 'equity' and (not m.get('currency') or m.get('adjusted') not in (True,False)):
        raise ValueError('Equity prices require currency and explicit adjustment status')
    if asset == 'freight' and not m.get('unit'):
        raise ValueError('Freight history requires an explicit unit')

def import_csv(root, csv_path, manifest_path):
    m=json.loads(Path(manifest_path).read_text(encoding='utf8'))
    asset=m.get('assetType')
    if asset not in ('equity','freight'):raise ValueError('Unknown asset type')
    valid_manifest(m,asset)
    key=m.get('ticker') if asset=='equity' else m.get('routeCode')
    if not isinstance(key,str) or not re.fullmatch(r'[A-Za-z0-9.\-_=^]{1,40}',key):raise ValueError('Invalid ticker/route')
    if asset=='equity':
        watchlist=json.loads((root/'watchlist.json').read_text(encoding='utf8'))['tickers']
        extra = set()
        context_path=root/'data/context.json'
        if context_path.exists():
            context=json.loads(context_path.read_text(encoding='utf8'))
            extra = {c.get(k) for c in context.get('shareClasses',[]) for k in ('a','b')}
        if key not in {w['ticker'] for w in watchlist}|extra:raise ValueError('Ticker not on watchlist or supported A/B pair')
    else:
        routes=json.loads((root/'data/freight-routes.json').read_text(encoding='utf8'))['routes']
        route=next((r for r in routes if r['code']==key),None)
        if not route or route['unit'] != m['unit']:raise ValueError('Route code or unit differs from official catalog')
    series={}
    with Path(csv_path).open(encoding='utf-8-sig',newline='') as f:
        for row in csv.DictReader(f):
            d=date.fromisoformat(row['date']); v=float(row['close'] if asset=='equity' else row['value'])
            if not math.isfinite(v) or v<=0:raise ValueError('Values must be finite and positive')
            if d>datetime.now(timezone.utc).date():raise ValueError('Future observation is not valid')
            if str(d) in series: raise ValueError('Duplicate date '+str(d))
            entry={'date':str(d),'close' if asset=='equity' else 'value':round(v,8)}
            if asset=='equity':
                vol=row.get('volume','')
                entry['volume']=int(vol) if vol.strip() else None
                if entry['volume'] is not None and entry['volume']<0:raise ValueError('Negative volume')
            series[str(d)]=entry
    if len(series)<3:raise ValueError('Need at least 3 real dated observations')
    data=root/'data'/('history' if asset=='equity' else 'freight-history')
    data.mkdir(exist_ok=True,parents=True)
    common={'source':m['provider'],'sourceUrl':m['sourceUrl'],'licenseReference':m['licenseReference'],
            'redistributionPermitted':True,'updated':datetime.now(timezone.utc).isoformat(timespec='seconds')}
    payload=({**common,'ticker':key,'currency':m['currency'],'adjusted':m['adjusted'],'bars':list(series.values())} if asset=='equity'
             else {**common,'code':key,'unit':m['unit'],'observations':list(series.values())})
    payload['bars' if asset=='equity' else 'observations'].sort(key=lambda x:x['date'])
    dest=data/(key+'.json')
    temp=dest.with_suffix('.tmp');temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8');temp.replace(dest)
    return dest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('csv');parser.add_argument('manifest');a=parser.parse_args()
    print(import_csv(ROOT, a.csv, a.manifest))
