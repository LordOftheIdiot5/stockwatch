"""V121 Market Pulse browser acceptance; all source responses are test-only.
No example numbers are written to the public data/ directory or shown to users.
"""
from datetime import datetime, timezone, timedelta, date
from pathlib import Path
from playwright.sync_api import sync_playwright
import functools, http.server, json, threading

ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://example.gov/pulse-source-report'
WIDTHS=(320,390,768,1440,1920)

def month_before(day):
    last=day.replace(day=1)-timedelta(days=1)
    return last.year,last.month
def quarter_before(day):
    current=(day.month-1)//3+1
    quarter=current-1
    year=day.year
    if quarter==0:year-=1;quarter=4
    return year,quarter
def make_fixture():
    today=datetime.now(timezone.utc).date()
    latest_week=today-timedelta(days=(today.weekday()-2)%7)
    prev_week=latest_week-timedelta(days=7)
    y,m=month_before(today)
    prev_y,prev_m=month_before(date(y,m,1))
    year,q=quarter_before(today)
    def q_end(year,quarter):
        month=quarter*3
        following=date(year+1,1,1) if month==12 else date(year,month+1,1)
        return (following-timedelta(days=1)).isoformat()
    issuer_end=q_end(year,q)
    issuer_previous=q_end(year if q>1 else year-1,q-1 if q>1 else 4)
    def row(key,period,unit,older,newer):
        return {'key':key,'period':period,'unit':unit,
          'sourceUrl':SOURCE,'history':[older,newer]}
    def oldnew(a,b,periods,field='date'):
        return [{field:periods[0],'value':a},{field:periods[1],'value':b}]
    latest_month=f'{y}-{m:02d}'
    prev_month=f'{prev_y}-{prev_m:02d}'
    quarter=f'{year}-Q{q}'
    prior_quarter=f'{year-1}-Q{q}'
    last_year=today.year-1; prior_year=last_year-1
    issuer_series=lambda key,unit,old,new:{'key':key,'unit':unit,'observations':[
       {'periodEnd':issuer_previous,'value':old,'sourceUrl':SOURCE},
       {'periodEnd':issuer_end,'value':new,'sourceUrl':SOURCE}
    ]}
    return {
      'freight':{'generated':today.isoformat(),'series':[
        row('usda:gulf-japan-index',latest_week.isoformat(),'index, 2017 = 100',
            *oldnew(185.61,184.97,[prev_week.isoformat(),latest_week.isoformat()])),
        row('usda:pnw-japan-index',latest_week.isoformat(),'index, 2017 = 100',
            *oldnew(187.65,187.65,[prev_week.isoformat(),latest_week.isoformat()]))
      ]},
      'connectivity':{'generated':today.isoformat(),'source':{'sourceUrl':SOURCE},'series':[
        row('unctad:lsci-monthly:denmark',latest_month,'index',
            *oldnew(86.93735,81.59456,[prev_month+'-01',latest_month+'-01'])),
        row('unctad:lsci-monthly:sweden',latest_month,'index',
            *oldnew(109.9681,105.94177,[prev_month+'-01',latest_month+'-01'])),
        row('unctad:lsci-monthly:norway',latest_month,'index',
            *oldnew(55.28495,56.45433,[prev_month+'-01',latest_month+'-01']))
      ]},
      'roro':{'observedOn':today.isoformat(),'sourceUrl':SOURCE,'series':[
        {'countryCode':'NO','period':quarter,'unit':'thousand tonnes',
          'history':oldnew(1094,1161,[prior_quarter,quarter],'period')},
        {'countryCode':'SE','period':quarter,'unit':'thousand tonnes',
          'history':oldnew(11761,12166,[prior_quarter,quarter],'period')},
        {'countryCode':'NL','period':quarter,'unit':'thousand tonnes',
          'history':oldnew(6806,6856,[prior_quarter,quarter],'period')}
      ]},
      'ports':{'generated':today.isoformat(),'source':{'sourceUrl':SOURCE},'series':[
        row('worldbank:container-port-teu:WLD',str(last_year),'TEU',
          *oldnew(853611611,913279048,[f'{prior_year}-12-31',f'{last_year}-12-31'])),
        row('worldbank:container-port-teu:VNM',str(last_year),'TEU',
          *oldnew(21069746,24423183,[f'{prior_year}-12-31',f'{last_year}-12-31'])),
        row('worldbank:container-port-teu:NOR',str(last_year),'TEU',
          *oldnew(882560,862983,[f'{prior_year}-12-31',f'{last_year}-12-31']))
      ]},
      'company':{'compiledOn':today.isoformat(),'companies':[{'ticker':'WAWI.OL','series':[
        issuer_series('net_freight','USD/m³',61.4,64.4),
        issuer_series('transport_volume','million m³',13.6,13.2),
        issuer_series('backlog','USD billion',6.5,5.8)
      ]}]},
      'rates':{'reportedAt':today.isoformat(),'isBrokerRate':False,'sourceUrl':SOURCE,'rates':[
        {'id':'us-gulf-japan-grain-2026-11-12','observationDate':latest_week.isoformat(),'value':72.75},
        {'id':'pnw-japan-grain-2026-11-12','observationDate':latest_week.isoformat(),'value':39.5}
      ]}
    }

def run():
    fixture=make_fixture()
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
        functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    failures=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                for width in WIDTHS:
                    for theme in ('dark','light'):
                        page=browser.new_page(viewport={'width':width,'height':940},reduced_motion='reduce')
                        errors=[];requests=[]
                        page.on('pageerror',lambda x:errors.append(str(x)))
                        page.add_init_script('localStorage.setItem("stockwatch-theme",'+json.dumps(theme)+')')
                        for name,payload in fixture.items():
                            path={'freight':'shipping-open','connectivity':'shipping-connectivity',
                                  'roro':'shipping-roro-traffic','ports':'shipping-ports',
                                  'company':'company-operating-metrics',
                                  'rates':'shipping-usda-ocean-rates-s1'}[name]
                            page.route('**/data/'+path+'.json?pulse=v121',
                              lambda route,value=payload,key=name:(
                                requests.append(key),
                                route.fulfill(status=200,content_type='application/json',body=json.dumps(value))
                              ))
                        page.goto(f'http://127.0.0.1:{server.server_port}/shipping.html',
                            wait_until='domcontentloaded',timeout=30000)
                        page.locator('#shippingMapPins .sw-atlas-point').first.wait_for(timeout=30000)
                        page.locator('#sw121SignalCards .sw121-signal-card').first.wait_for(timeout=20000)
                        assert page.locator('#sw121MarketPulse').count()==1
                        assert page.locator('#sw121SignalCards article').count()==6,(width,theme)
                        assert page.locator('#sw121SourceStatus').inner_text().startswith('6 source-dated')
                        assert len(requests)==6,(width,theme,requests)
                        assert page.locator('.sw121-map-peek').is_visible()
                        assert page.locator('#shippingMapPins .sw-atlas-point').count()==40
                        assert page.locator('#sw121SignalCards article[data-signal="global-container-history"]').count()==1
                        assert 'Historical' in page.locator('article[data-signal="global-container-history"]').inner_text()
                        assert '-6.1%' in page.locator('article[data-signal="nordic-liner-network"]').inner_text()
                        assert '+6.1%' in page.locator('article[data-signal="nordic-roro-yoy"]').inner_text()
                        assert '72.75' in page.locator('article[data-signal="usda-grain-indications"]').inner_text()
                        assert '2017=100' in page.locator('article[data-signal="usda-grain-week"]').inner_text()
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 3'),(width,theme,'overflow')
                        page.locator('[data-filter="liner_connectivity"]').click()
                        assert page.locator('#sw121SignalCards article').count()==1
                        page.locator('[data-filter="all"]').click()
                        assert page.locator('#sw121SignalCards article').count()==6
                        if width in (390,1440) and theme=='dark':
                            screenshot=ROOT/'workspace-previews'/f'maritime-pulse-v121-{width}.png'
                            screenshot.parent.mkdir(parents=True,exist_ok=True)
                            page.locator('#sw121MarketPulse').screenshot(
                                path=str(screenshot),animations='disabled',timeout=30000)
                        camera=page.locator('#shippingMapSvg').get_attribute('viewBox')
                        page.locator('article[data-signal="nordic-roro-yoy"] .sw121-map-context').click()
                        assert page.locator('#shippingMapSvg').get_attribute('viewBox')!=camera
                        page.locator('#shippingMapPick').select_option('NL-RTM')
                        assert page.locator('#shippingMapInspector').is_visible()
                        assert not page.locator('.sw121-map-peek').is_visible()
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 3')
                        # Re-attachment after app mutation must not duplicate pulse.
                        page.evaluate("document.getElementById('v4app').append(document.createElement('span'))")
                        page.wait_for_timeout(110)
                        assert page.locator('#sw121MarketPulse').count()==1
                        assert not errors,(width,theme,errors)
                        failures.append({'width':width,'theme':theme,'source_groups':6,
                                        'map_ports':40,'overflows':0,'page_errors':0})
                        page.close()
                # Missing upstream snapshot: original available cards survive,
                # and the missing field must never be replaced with zero.
                page=browser.new_page(viewport={'width':390,'height':900})
                for name,payload in fixture.items():
                    path={'freight':'shipping-open','connectivity':'shipping-connectivity',
                          'roro':'shipping-roro-traffic','ports':'shipping-ports',
                          'company':'company-operating-metrics',
                          'rates':'shipping-usda-ocean-rates-s1'}[name]
                    if name=='freight':
                        page.route('**/data/'+path+'.json?pulse=v121',
                            lambda route:route.fulfill(status=503,body='Unavailable'))
                    else:
                        page.route('**/data/'+path+'.json?pulse=v121',
                            lambda route,value=payload:route.fulfill(status=200,
                                content_type='application/json',body=json.dumps(value)))
                page.goto(f'http://127.0.0.1:{server.server_port}/shipping.html',
                    wait_until='domcontentloaded',timeout=30000)
                page.locator('#sw121SignalCards article').first.wait_for(timeout=20000)
                assert page.locator('#sw121SignalCards article').count()==5
                assert '1 dataset unavailable' in page.locator('#sw121SourceStatus').inner_text()
                assert page.locator('article[data-signal="usda-grain-week"]').count()==0
                page.close()
            finally: browser.close()
    finally:server.shutdown();server.server_close()
    assert len(failures)==10
    print(json.dumps({'status':'PASS','results':failures,'missing_source_rejected':True},indent=2))

if __name__=='__main__':run()
