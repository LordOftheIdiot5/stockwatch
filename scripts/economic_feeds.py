"""Official FRED/EIA series importer; credentials from GitHub Actions only."""
import json,math,os,re,urllib.parse,urllib.request,urllib.error,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FRED={'DGS2':('US 2-year Treasury yield','percent'),'DGS10':('US 10-year Treasury yield','percent'),'DFF':('US effective federal funds rate','percent'),'UNRATE':('US unemployment rate','percent')}
EIA={'RBRTE':('Brent crude spot price','USD/barrel'),'RWTC':('WTI Cushing crude spot price','USD/barrel')}
UA='StockwatchResearch/1.0 (+https://stocks.nordl.dev)'
def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
def request(url,timeout=22,attempts=1):
    """Retry only temporary transport/API failures; never disclose token URLs."""
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req,timeout=timeout) as response:
                raw=response.read(2000001)
                if len(raw)>2000000: raise ValueError('too_many_bytes')
            return json.loads(raw)
        except urllib.error.HTTPError as err:
            if attempt==attempts-1 or err.code not in (429,500,502,503,504):raise
        except (TimeoutError,urllib.error.URLError):
            if attempt==attempts-1:raise
        time.sleep(2*(attempt+1))
def number(value):
    try:
        n=float(value)
        return round(n,6) if math.isfinite(n) else None
    except (ValueError,TypeError): return None
def history(rows, date_field, val_field):
    points={}
    for row in rows:
        d=str(row.get(date_field) or '')
        n=number(row.get(val_field))
        if re.fullmatch(r'20\d\d-\d\d-\d\d',d) and n is not None: points[d]=n
    return [{'date':d,'value':n} for d,n in sorted(points.items())[-370:]]
def fred(key,series_id):
    params=urllib.parse.urlencode({'series_id':series_id,'api_key':key,'file_type':'json','limit':370,'sort_order':'desc'})
    data=request('https://api.stlouisfed.org/fred/series/observations?'+params)
    if not isinstance(data.get('observations'),list):raise ValueError('invalid_fred_response')
    rows=history(data['observations'],'date','value')
    if not rows:raise ValueError('empty_fred_response')
    return observation('fred',series_id,*FRED[series_id],rows,'US','https://fred.stlouisfed.org/series/'+series_id,
        'FRED: source US Treasury/Federal Reserve/BLS; attribute and verify per-series use rights')
def eia(key,series_id):
    params=urllib.parse.urlencode([('api_key',key),('frequency','daily'),('data[0]','value'),('facets[series][]',series_id),('sort[0][column]','period'),('sort[0][direction]','desc'),('length','370')])
    data=request('https://api.eia.gov/v2/petroleum/pri/spt/data/?'+params,timeout=60,attempts=2)
    raw=data.get('response',{}).get('data')
    if not isinstance(raw,list):raise ValueError('invalid_eia_response')
    rows=history([r for r in raw if r.get('series')==series_id],'period','value')
    if not rows:raise ValueError('empty_eia_response')
    return observation('eia',series_id,*EIA[series_id],rows,'Global','https://www.eia.gov/opendata/',
        'Source: U.S. Energy Information Administration (EIA); attribution required')
def observation(provider,code,label,unit,rows,country,source,license):
    return {'key':provider+':'+code,'provider':provider,'label':label,'unit':unit,'country':country,
            'frequency':'business_day' if provider=='eia' else 'official_series',
            'period':rows[-1]['date'],'value':rows[-1]['value'],'history':rows,
            'sourceUrl':source,'license':license,'observedAt':timestamp()}
def build(root=ROOT):
    path=root/'data/economic-feeds.json'
    try: old=json.loads(path.read_text(encoding='utf8'))
    except (OSError,ValueError): old={}
    stored={s['key']:s for s in old.get('series',[]) if isinstance(s,dict) and s.get('key')}
    statuses={}
    for name,env,series,collector in [('fred','STOCKWATCH_FRED_API_KEY',FRED,fred),('eia','STOCKWATCH_EIA_API_KEY',EIA,eia)]:
        key=os.getenv(env,'').strip()
        prior=(old.get('sources') or {}).get(name,{})
        source='https://fred.stlouisfed.org/' if name=='fred' else 'https://www.eia.gov/opendata/'
        if not key:
            statuses[name]={'status':'awaiting_key','lastSuccessAt':prior.get('lastSuccessAt'),'sourceUrl':source}
            continue
        count,errors=0,[]
        for code in series:
            try:
                item=collector(key,code)
                stored[item['key']]=item
                count+=1
            except Exception as err:
                issue={'series':code,'errorType':type(err).__name__}
                if isinstance(err,urllib.error.HTTPError):issue['httpStatus']=int(err.code)
                errors.append(issue) # Never serialize errors or request URLs containing keys
        statuses[name]={'status':'ok' if count==len(series) else 'partial_error' if count else 'error',
                       'records':count,'expected':len(series),'errors':errors,'sourceUrl':source,
                       'lastSuccessAt':timestamp() if count else prior.get('lastSuccessAt')}
    output={'generated':timestamp(),'notice':'Official dated observations, not tradable quotes; per-series reuse rights apply.',
            'series':sorted(stored.values(),key=lambda s:s['key']),'sources':statuses}
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
    print('Economic sources: '+', '.join(k+'='+v['status'] for k,v in statuses.items())+'; series='+str(len(stored)))
    return output
if __name__=='__main__':build()
