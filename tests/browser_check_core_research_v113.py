"""V113: source-safe company → terminal → comparison workflow, no legacy history 404s."""
import functools
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
COMPANY='NHY.OL'

def main():
 server=http.server.ThreadingHTTPServer(
  ('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 base=f'http://127.0.0.1:{server.server_port}/'
 result=[]
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
   try:
    for width in (390,1440,1920):
     context=browser.new_context(viewport={'width':width,'height':900},reduced_motion='reduce')
     try:
      page=context.new_page()
      requests=[];errors=[];http_errors=[]
      page.on('request',lambda req:requests.append(req.url) if '/data/history/' in req.url else None)
      page.on('pageerror',lambda err:errors.append(str(err)))
      page.on('response',lambda resp:http_errors.append((resp.status,resp.url)) if resp.status>=400 and '/data/history/' in resp.url else None)
      try:
       page.goto(base+'company.html?ticker='+COMPANY+'&section=filings',wait_until='domcontentloaded',timeout=30000)
       panel=page.locator('.sw-company-research[data-sw113-ready="true"]')
       panel.wait_for(timeout=30000)
       assert panel.get_attribute('data-sw110c-tab')=='filings'
       actions=panel.locator('.sw113-research-action')
       assert actions.count()==4,(width,actions.count())
       expected={
        'terminal.html?ticker=NHY.OL',
        'compare.html?ticker=NHY.OL',
        'intelligence.html?ticker=NHY.OL',
        'news.html?q=NHY.OL'}
       assert set(actions.evaluate_all('(els)=>els.map(el=>el.getAttribute("href"))'))==expected
       page.wait_for_function("document.querySelector('#individualChart')?.textContent?.includes('No licensed dated prices')",timeout=30000)
       assert 'No licensed dated prices' in panel.locator('#individualChart').inner_text()
       assert page.locator('a.sw113-research-action[href="terminal.html?ticker=NHY.OL"]').is_visible()
       assert not requests,(width,requests)
       assert not errors,(width,errors)
       assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3')
       panel.locator('[data-company-tab=financials]').click()
       assert 'section=financials' in page.url
       assert panel.locator('[data-company-section=financials]').is_visible()
       if width==1440:
        (ROOT/'workspace-previews').mkdir(exist_ok=True)
        page.screenshot(path=str(ROOT/'workspace-previews'/'v113-company-1440.png'),animations='disabled')
       # Follow the exact company link; never fall back to persisted selection.
       page.locator('a.sw113-research-action[href="terminal.html?ticker=NHY.OL"]').click()
       page.locator('#terminalInstrument').wait_for(timeout=30000)
       page.wait_for_function("document.querySelector('#terminalInstrument')?.textContent?.includes('NHY.OL')",
        timeout=30000)
       assert 'NHY.OL' in page.locator('#terminalInstrument').inner_text()
       assert not errors,(width,errors)
       page.goto(base+'compare.html?ticker=NHY.OL',wait_until='domcontentloaded',timeout=30000)
       page.locator('#pick0').wait_for(timeout=30000)
       page.wait_for_function("document.querySelector('#pick0')?.value === 'NHY.OL'",timeout=30000)
       assert page.locator('#pick0').input_value()=='NHY.OL'
       page.locator('#compareHistoryStatus').wait_for(timeout=30000)
       page.wait_for_function("document.querySelector('#compareHistoryStatus')?.textContent?.includes('Licensed dated history is not connected')",timeout=30000)
       assert 'Licensed dated history is not connected' in page.locator('#compareHistoryStatus').inner_text()
       assert page.locator('.sw113-company-link').count()>=2
       assert not requests,(width,requests)
       assert not errors,(width,errors)
       if width==1440:
        page.screenshot(path=str(ROOT/'workspace-previews'/'v113-compare-1440.png'),animations='disabled')
       page.goto(base+'spreads.html',wait_until='domcontentloaded',timeout=30000)
       page.locator('#v4app').wait_for(timeout=30000)
       page.wait_for_timeout(500)
       assert not requests,(width,requests)
       assert not http_errors,(width,http_errors)
       assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3')
       assert not errors,(width,errors)
       result.append({'width':width,'ticker':COMPANY,'noMissingHistoryFetch':True})
      finally:page.close()
     finally:context.close()
   finally:browser.close()
 finally:server.shutdown();server.server_close()
 print(json.dumps({'v113':'pass','views':len(result),'result':result}))

if __name__=='__main__':main()
