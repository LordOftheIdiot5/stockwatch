"""V110b: tested source-honest compact terminal and reversible menu layouts."""
import functools,http.server,threading,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
  functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 out=ROOT/'workspace-previews';out.mkdir(exist_ok=True)
 checks=[]
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
   for route in ('index','company','stocks','shipping','commodities','news'):
    for width in (390,1440):
     page=browser.new_page(viewport={'width':width,'height':900},reduced_motion='reduce')
     errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
     suffix='?ticker=NHY.OL' if route=='company' else ''
     page.goto(f'http://127.0.0.1:{server.server_port}/{route}.html{suffix}',
       wait_until='domcontentloaded',timeout=30000)
     assert page.locator('link[href*="workspace-density-v110b.css"]').count()==1
     if route=='index':
      page.locator('#overviewMacroSeries').wait_for(timeout=30000)
      heat=page.locator('.sw98-market-secondary .sw-ws-heatmap')
      watch=page.locator('#overviewWatchlist');watch.wait_for(timeout=30000)
      assert page.locator('#globalMarketPulse').count()==1
      assert page.locator('.sw98-intelligence-rail .sw-overview-news').count()==1
      if width==1440:
       cols=page.locator('.sw98-market-secondary').evaluate(
        '(x)=>getComputedStyle(x).gridTemplateColumns').split(' ')
       assert len(cols)==3,cols
       assert watch.bounding_box()['y'] < heat.bounding_box()['y']+280
       assert page.locator('.sw110-heat-companion').evaluate(
         '(x)=>getComputedStyle(x).display')=='contents'
       assert page.locator('.sw98-intelligence-rail').evaluate(
         '(x)=>getComputedStyle(x).display')=='contents'
       assert heat.bounding_box()['y']<860,heat.bounding_box()
      else:
       assert watch.bounding_box()['y']>=heat.bounding_box()['y']
     elif route=='company':
      page.locator('.sw-company-heading h2').wait_for(timeout=30000)
      assert page.locator('.sw-company-tabs [data-company-tab]').count()==7
      assert page.locator('#companyDriverMap').count()==1
      assert page.locator('#companyHistorySource').count()==1
     else:
      nav=page.locator('.sw110b-jump');nav.wait_for(timeout=30000)
      toggle=nav.locator('.sw110b-layout-toggle')
      assert toggle.get_attribute('aria-pressed')=='false'
      toggle.click()
      assert 'sw110b-spacious' in page.locator('body').get_attribute('class')
      assert toggle.get_attribute('aria-pressed')=='true'
      toggle.click()
      assert 'sw110b-spacious' not in page.locator('body').get_attribute('class')
     assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'),(route,width)
     assert not errors,(route,width,errors)
     if width==1440 and route in ('index','company','stocks'):
      page.screenshot(path=str(out/f'v110b-{route}-1440.png'),animations='disabled')
     checks.append({'route':route,'width':width});page.close()
   browser.close()
 finally:
  server.shutdown();server.server_close()
 print(json.dumps({'result':'pass','views':len(checks),'routes':sorted(set(x['route'] for x in checks))}))
if __name__=='__main__':main()
