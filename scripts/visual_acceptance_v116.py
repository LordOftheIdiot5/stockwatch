"""V116: 19-route visual evidence matrix and source-failure acceptance.

Covers source-rendered DOM at six viewport sizes and both themes. The zoom
check uses CSS zoom as a diagnostic *proxy*, not a claimed manual 200% audit.
Do not mark owner-approved screenshot parity complete from test exit status.
"""
import functools
import hashlib
import http.server
import json
import threading
from datetime import datetime,timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'visual-audit'/'v116'
ROUTES={
 'overview':'index.html','stocks':'stocks.html','company':'company.html?ticker=NHY.OL',
 'terminal':'terminal.html','spreads':'spreads.html','shipping':'shipping.html',
 'commodities':'commodities.html','news':'news.html','calendar':'calendar.html',
 'compare':'compare.html','shorts':'shorts.html','intelligence':'intelligence.html',
 'directory':'directory.html','history':'price-history.html',
 'research':'research.html','health':'health.html','welcome':'welcome.html',
 'datasets':'data-products.html','search':'search.html'
}
VIEWPORTS=(320,390,768,1024,1440,1920)
REFERENCE={'file':'stockwatch-approved-full-width-overview-v1.png',
 'sha256':'df85998bd202dd9e4b3832a85edfaaf9fde78a417af4dcc3c7ced9e076be7b00',
 'width':1672,'height':941,'kind':'illustrative design target, NOT market data'}
MEASURE="""() => {
 const html=document.documentElement;
 const nav=document.querySelector('a[href="index.html"]');
 const head=document.querySelector('main h1')||document.querySelector('h1');
 const heat=document.querySelector('.sw98-market-secondary .sw-ws-heatmap');
 const chart=document.querySelector('.sw98-primary .sw92-focus-chart');
 const breadth=document.querySelector('.sw98-primary .sw92-focus-summary');
 const news=document.querySelector('.sw98-primary .sw-overview-news');
 const map=document.querySelector('.sw110d-market-coverage');
 const watch=document.querySelector('.sw99-watchlist');
 const b=el=>{if(!el)return null;const r=el.getBoundingClientRect();return {
  x:Math.round(r.x),y:Math.round(r.y),width:Math.round(r.width),height:Math.round(r.height)
 }};
 return {scrollWidth:html.scrollWidth,viewportWidth:innerWidth,
  height:html.scrollHeight,visibleText:(document.body.innerText||'').length,
  heading:head?.textContent?.trim().slice(0,100)||null,
  overviewLink:!!nav,chart:b(chart),heatmap:b(heat),breadth:b(breadth),
  news:b(news),coverage:b(map),watchlist:b(watch),
  bodyTheme:document.body.getAttribute('data-theme')
 };
}"""
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
  functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 base='http://127.0.0.1:'+str(server.server_port)+'/'
 records=[]
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
   try:
    for width in VIEWPORTS:
     for theme in ('dark','light'):
      context=browser.new_context(viewport={'width':width,'height':941},
        reduced_motion='reduce',device_scale_factor=1)
      context.add_init_script('localStorage.setItem("stockwatch-theme",'+json.dumps(theme)+')')
      try:
       for name,path in ROUTES.items():
        page=context.new_page()
        errors=[];failed=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.on('requestfailed',lambda request:failed.append(request.url)
          if request.url.startswith(base) else None)
        try:
         response=page.goto(base+path,wait_until='domcontentloaded',timeout=30000)
         try:
          page.wait_for_function("document.body.innerText.length>60",timeout=10000)
         except Exception:pass
         page.wait_for_timeout(120)
         m=page.evaluate(MEASURE)
         m.update(route=name,path=path,width=width,theme=theme,
          http=response.status if response else None,
          pageErrors=errors[:5],failedRequests=failed[:5],
          overflow=m['scrollWidth']>m['viewportWidth']+3,
          blank=m['visibleText']<60 or m['heading'] is None)
         records.append(m)
         if width in (390,1440):
          screenshots=[('top',0)]
          if theme=='dark':
           screenshots.extend([
            ('middle',min(m['height']-941,941)),
            ('bottom',max(0,m['height']-941))
           ])
          for suffix,scroll in screenshots:
           if scroll>0:page.evaluate('(y)=>scrollTo(0,y)',scroll);page.wait_for_timeout(70)
           page.screenshot(path=str(OUT/f'{name}-{width}-{theme}-{suffix}.png'),
            animations='disabled',timeout=15000)
        except Exception as e:
         records.append({'route':name,'width':width,'theme':theme,
          'criticalError':str(e)[:600]})
        finally:page.close()
      finally:context.close()
    # Failure-only fixture on current real published files (never shipped).
    fixture=browser.new_page(viewport={'width':1440,'height':900})
    try:
     fixture.route('**/data/daily-price-coverage-v105.json*',
       lambda route:route.abort('failed'))
     fixture.goto(base+'index.html',wait_until='domcontentloaded',timeout=30000)
     fixture.locator('.sw110d-market-coverage').wait_for(timeout=30000)
     fixture.wait_for_timeout(350)
     text=fixture.locator('.sw110d-market-coverage').inner_text()
     stale={'test':'coverage request failure','fallbackText':text[:280],
      'honestFallback':'Dated exchange coverage is unavailable' in text,
      'unlicensedMapPins':fixture.locator('.sw110e-pin').count()}
    finally:fixture.close()
    # CSS zoom is a proxy; native user browser zoom must be inspected separately.
    zoom=browser.new_page(viewport={'width':1440,'height':900})
    try:
     zoom.goto(base+'index.html',wait_until='domcontentloaded',timeout=30000)
     zoom.locator('#overviewMacroSeries').wait_for(timeout=30000)
     zoom.evaluate("document.documentElement.style.zoom='2'")
     zoom.wait_for_timeout(100)
     metric=zoom.evaluate(MEASURE)
     zoom_meta={'test':'CSS 200% zoom proxy, not native browser zoom',
       'overflow':metric['scrollWidth']>metric['viewportWidth']+3,
       'scrollWidth':metric['scrollWidth'],'viewportWidth':metric['viewportWidth']}
     zoom.screenshot(path=str(OUT/'overview-1440-zoom-2x-proxy.png'),
      animations='disabled',timeout=15000)
    finally:zoom.close()
   finally:browser.close()
 finally:server.shutdown();server.server_close()
 fail=[x for x in records if x.get('criticalError') or x.get('http')!=200 or
   x.get('pageErrors') or x.get('failedRequests') or x.get('overflow') or x.get('blank')]
 report={'version':'V116a','generatedUtc':datetime.now(timezone.utc).isoformat(),
   'reference':REFERENCE,'sampleSource':'actual repository data and published files',
   'matrix':{'routes':len(ROUTES),'widths':VIEWPORTS,'themes':['dark','light'],
    'expected':len(ROUTES)*len(VIEWPORTS)*2,'tested':len(records),'criticalCount':len(fail)},
   'failureFixture':stale,'zoomProxy':zoom_meta,
   'manualSignoffRequired':['approved first-screen visual parity','native browser 200% zoom',
    'light/dark contrast sampling','keyboard flow in a real browser',
    'licensed global-market data availability'],
   'records':records}
 (OUT/'acceptance-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(json.dumps({'matrix':report['matrix'],'failures':fail[:8],
   'offline':stale,'zoom':zoom_meta},indent=2),flush=True)
 assert len(records)==len(ROUTES)*len(VIEWPORTS)*2
 assert not fail,('V116 critical browser/page failures',fail[:8])
 assert stale['honestFallback'] and stale['unlicensedMapPins']==0

if __name__=='__main__':main()
