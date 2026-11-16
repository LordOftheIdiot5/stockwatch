"""Run against the actual repository, no synthetic market observations.

Usage: python -m pip install playwright
       python -m playwright install chromium
       python tests/browser_check_v21.py
"""
import functools
import http.server
import json
import pathlib
import threading
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'workspace-previews'
class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
def main():
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    OUT.mkdir(exist_ok=True)
    try:
      with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        for width,height in [(1440,1000),(390,844)]:
          for theme in ('dark','light'):
            page=browser.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
            page.add_init_script(f"localStorage.setItem('stockwatch-theme',{json.dumps(theme)})")
            errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
            page.goto(base+'/index.html',wait_until='domcontentloaded')
            page.locator('#workspaceHeatmap').wait_for(timeout=20000)
            assert page.locator('.sw-ws-module').count()==9
            assert page.locator('body').get_attribute('data-theme')==theme
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 2'),f'Horizontal overflow: {width}, {theme}'
            first=page.locator('.sw-heat-cell')
            options=page.locator('#workspaceSector option')
            if first.count() and options.count()>1:
                page.locator('#workspaceSector').select_option(index=1)
                assert page.locator('.sw-heat-sector').count()==1
                page.locator('#workspaceSector').select_option('all')
            assert not errors,errors
            page.screenshot(path=str(OUT/f'overview-{width}-{theme}.png'),full_page=True)
            page.close()
        page=browser.new_page(viewport={'width':1440,'height':1000})
        errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
        page.goto(base+'/stocks.html',wait_until='domcontentloaded')
        page.locator('#stockPage').wait_for(timeout=20000)
        count=page.locator('#stocksRows tr').count()
        assert 1<=count<=50,count
        next_btn=page.locator('#stockNext')
        if next_btn.is_enabled():
            next_btn.click()
            assert page.locator('#stockPage').inner_text().startswith('Page 2 ')
        watchlist=json.loads((ROOT/'watchlist.json').read_text())['tickers']
        ticker=watchlist[0]['ticker']
        page.locator('#stkSearch').fill(ticker)
        assert page.locator('#stockPage').inner_text().startswith('Page 1 ')
        page.locator('[data-stock]').first.click()
        page.locator('.sw-identity-panel').wait_for()
        assert 'FIGI candidate' in page.locator('.sw-identity-panel').inner_text()
        assert not errors,errors
        page.screenshot(path=str(OUT/'company-research.png'),full_page=True)
        browser.close()
    finally:
      server.shutdown();server.server_close()
if __name__=='__main__':main()
