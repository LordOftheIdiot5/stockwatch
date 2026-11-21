"""V110c actual company focused tabs and complete source-backed full report."""
import functools,http.server,threading,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def main():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
   functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 out=ROOT/'workspace-previews';out.mkdir(exist_ok=True)
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
   results=[]
   for ticker in ('NOVO-B.CO','NHY.OL','SALM.OL'):
    for width in (390,1440):
     page=browser.new_page(viewport={'width':width,'height':900},reduced_motion='reduce')
     errors=[];page.on('pageerror',lambda x:errors.append(str(x)))
     page.goto(f'http://127.0.0.1:{server.server_port}/company.html?ticker={ticker}',
       wait_until='domcontentloaded',timeout=30000)
     panel=page.locator('.sw-company-research')
     panel.wait_for(timeout=30000)
     page.wait_for_function("document.querySelector('.sw-company-research')?.dataset.sw110cMode==='focus'",timeout=30000)
     nav=panel.locator('.sw-company-tabs')
     tabs=nav.locator('[data-company-tab]')
     full=nav.locator('.sw110c-mode')
     assert tabs.count()==7
     assert full.get_attribute('aria-pressed')=='false'
     assert panel.get_attribute('data-sw110c-tab')=='chart'
     assert panel.locator('[data-company-section=chart]').is_visible()
     assert panel.locator('#companyDriverMap').is_visible()
     assert panel.locator('#companyHistorySource').count()==1
     assert not panel.locator('[data-company-section=financials]').is_visible()
     tabs.locator('[data-company-tab=financials]').click()
     assert panel.get_attribute('data-sw110c-tab')=='financials'
     assert panel.locator('[data-company-section=financials]').is_visible()
     assert not panel.locator('[data-company-section=chart]').is_visible()
     assert not panel.locator('#companyDriverMap').is_visible()
     assert tabs.locator('[data-company-tab=financials]').get_attribute('aria-pressed')=='true'
     page.evaluate("scrollTo(0,0)")
     assert tabs.locator('[data-company-tab=financials]').get_attribute('aria-current')=='location'
     for key in ('filings','peers','events','drivers','identity'):
      tabs.locator('[data-company-tab='+key+']').click()
      assert panel.get_attribute('data-sw110c-tab')==key
      assert panel.locator('[data-company-section='+key+']').is_visible()
     full.click()
     assert panel.get_attribute('data-sw110c-mode')=='full'
     assert full.get_attribute('aria-pressed')=='true'
     assert panel.locator('[data-company-section=chart]').is_visible()
     assert panel.locator('[data-company-section=financials]').is_visible()
     assert panel.locator('[data-company-section=identity]').is_visible()
     assert panel.locator('#companyDriverMap').is_visible()
     extra=panel.locator('.sw110c-more')
     assert extra.count()==1
     assert extra.get_attribute('open') is not None
     full.click()
     assert panel.get_attribute('data-sw110c-mode')=='focus'
     assert not panel.locator('[data-company-section=financials]').is_visible()
     tabs.locator('[data-company-tab=chart]').click()
     assert panel.locator('#companyDriverMap').is_visible()
     assert panel.locator('#companyHistorySource').count()==1
     assert not errors,(ticker,width,errors)
     assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'),(ticker,width)
     if width==1440:
      page.evaluate("scrollTo(0,0)")
      page.screenshot(path=str(out/f'v110c-company-{ticker.replace(".","-")}.png'),
       animations='disabled')
     results.append({'ticker':ticker,'width':width,'result':'pass'})
     page.close()
   browser.close()
 finally:
  server.shutdown();server.server_close()
 print(json.dumps({'v110c':'pass','views':len(results),'tickerCount':3}))
if __name__=='__main__':main()
