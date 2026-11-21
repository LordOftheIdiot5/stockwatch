"""V100 Nordic source notices test: real page, intercepted SOURCE TEST fixture only."""
import functools,http.server,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
     functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
   for width in (390,1440):
    page=browser.new_page(viewport={'width':width,'height':900})
    page.route('**/data/nasdaq-nordic-notices.json?*',lambda route:route.fulfill(
      status=200,content_type='application/json',
      body='{"items":[{"title":"Test original notice","published":"2026-11-21T03:00:00Z","url":"https://view.news.eu.nasdaq.com/view?id=testsource","category":"Nordic exchange notices"},{"title":"Hostile URL","published":"2026-11-21T03:00:00Z","url":"https://evil.example/"}],"sources":{"nordicInvestorNews":{"status":"ok"},"nordicExchangeNotices":{"status":"ok"}}}'))
    errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
    page.goto(f'http://127.0.0.1:{server.server_port}/news.html',
      wait_until='domcontentloaded',timeout=30000)
    page.locator('#nasdaqNoticeItems article').first.wait_for(timeout=30000)
    panel=page.locator('#nasdaqNordicNotices')
    assert panel.locator('article').count()==1
    assert panel.locator('article a').first.get_attribute('href')=='https://view.news.eu.nasdaq.com/view?id=testsource'
    assert 'Original Nasdaq Nordic notices' in panel.inner_text()
    assert 'Hostile URL' not in panel.inner_text()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+2')
    assert not errors,errors
    (ROOT/'workspace-previews').mkdir(exist_ok=True)
    page.screenshot(path=str(ROOT/'workspace-previews'/f'v100-notices-{width}.png'),
      animations='disabled')
    page.close()
   browser.close()
 finally:
  server.shutdown();server.server_close()
 print('V100 official source panel: mobile and desktop accepted')
if __name__=='__main__':main()
