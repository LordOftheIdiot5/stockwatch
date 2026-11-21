"""V114 real-browser secondary-market readability, source gates and task flow."""
import functools,http.server,json,threading
from datetime import datetime,timezone,timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PAGES={
 'spreads.html':('spreads',['#spreadPairs','#abRanking','#spreadDetail']),
 'shipping.html':('shipping',['#shippingBenchmarkAnchor','#routeCompare']),
 'commodities.html':('commodities',['#commodityTabs']),
 'shorts.html':('shorts',['#shortsDisclosurePanel']),
 'calendar.html':('calendar',['#calendarUpcoming','#calendarDisclosures'])
}
def main():
 server=http.server.ThreadingHTTPServer(
  ('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 base='http://127.0.0.1:'+str(server.server_port)+'/'
 results=[]
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
   try:
    for width in (390,1440):
     ctx=browser.new_context(viewport={'width':width,'height':900},reduced_motion='reduce')
     try:
      for path,(route,anchors) in PAGES.items():
       page=ctx.new_page()
       errors=[]
       page.on('pageerror',lambda err:errors.append(str(err)))
       try:
        if route=='calendar':
         now=datetime.now(timezone.utc)
         future=(now+timedelta(days=14)).date().isoformat()
         past=(now-timedelta(days=14)).date().isoformat()
         fixture={'generated':now.isoformat(),'items':[
          {'ticker':'TEST.OL','name':'Future test issuer','sector':'Testing',
           'date':future,'label':'Dated issuer earnings',
           'type':'earnings','verification':'verified',
           'sourceUrl':'https://example.org/future-issuer-report'},
          {'ticker':'OLD.OL','name':'Expired test issuer','sector':'Testing',
           'date':past,'label':'Expired earnings',
           'type':'earnings','verification':'verified',
           'sourceUrl':'https://example.org/old-issuer-report'}
         ]}
         page.route('**/data/events.json*',
           lambda route:route.fulfill(status=200,content_type='application/json',body=json.dumps(fixture)))
        response=page.goto(base+path,wait_until='domcontentloaded',timeout=30000)
        assert response and response.status==200,(path,'http')
        nav=page.locator('.sw114-tasknav')
        nav.wait_for(timeout=30000)
        links=nav.locator('a.sw114-task-link')
        assert links.count()>=len(anchors),(path,width,links.count())
        for selector in anchors:
         node=page.locator(selector)
         assert node.count()==1,(path,selector)
         assert links.locator('[href="'+selector+'"]').count()==1,(path,selector)
        assert not errors,(path,width,errors)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3'),(path,width,'overflow')
        assert nav.locator('.sw114-task-note').inner_text()
        if route=='calendar':
         rows=page.locator('#eventRows')
         rows.wait_for(timeout=30000)
         assert 'Future test issuer' in rows.inner_text()
         assert 'Expired test issuer' not in rows.inner_text()
         assert '1 events' in page.locator('#eventCount').inner_text()
         assert page.locator('.sw96-recent-filings').count()==1
        elif route=='commodities':
         page.locator('#commodityRows tr').first.wait_for(timeout=30000)
         assert page.locator('#commodityRows tr').count()>0
         assert page.locator('th').filter(has_text='Reported 1D').count()==1
         assert page.locator('th').filter(has_text='52-week range').count()==1
         assert page.locator('#commodityRows [role="meter"]').count()>0
        elif route=='shorts':
         assert page.locator('th').filter(has_text='Last reported').count()==1
         links_to_company=page.locator('#shortsDisclosurePanel a.sw114-company-link')
         if links_to_company.count():
          assert links_to_company.first.get_attribute('href').startswith('company.html?ticker=')
        elif route=='shipping':
         assert page.locator('#routeGrid').count()==1
         assert 'not' in nav.locator('.sw114-task-note').inner_text().lower() or 'different' in nav.locator('.sw114-task-note').inner_text().lower()
        elif route=='spreads':
         assert page.locator('#spreadPairs button').count()>0
         assert page.locator('#spreadGraph').count()==1
        first=links.first
        first.focus()
        first.press('Enter')
        assert page.url.endswith(first.get_attribute('href')),(path,width,'anchor')
        if width==1440:
         (ROOT/'workspace-previews').mkdir(exist_ok=True)
         page.screenshot(path=str(ROOT/'workspace-previews'/('v114-'+route+'-1440.png')),
          animations='disabled')
        results.append({'page':path,'width':width,'links':links.count()})
       finally:page.close()
     finally:ctx.close()
   finally:browser.close()
 finally:server.shutdown();server.server_close()
 print(json.dumps({'v114':'pass','views':len(results),'results':results}))

if __name__=='__main__':main()
