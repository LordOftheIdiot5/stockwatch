"""V112 browser gate: five editorial routes, dark/light, keyboard and real menus.

Source-backed pages use the repo's authentic published data; no quotes mocked.
"""
import functools
import http.server
import json
import os
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
ROUTES={'directory.html':'directory','research.html':'research',
        'search.html':'search','data-products.html':'data-products',
        'welcome.html':'welcome'}
WIDTHS=(320,390,768,1024,1440,1920)

def main():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
     functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 base='http://127.0.0.1:'+str(server.server_port)+'/'
 results=[]
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'],
       executable_path=os.environ.get('CHROMIUM_EXECUTABLE') or None)
   try:
    for width in WIDTHS:
     for theme in ('dark','light'):
      context=browser.new_context(viewport={'width':width,'height':900})
      context.add_init_script("localStorage.setItem('stockwatch-theme',"+json.dumps(theme)+")")
      try:
       for route,name in ROUTES.items():
        page=context.new_page()
        errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
        try:
         response=page.goto(base+route,wait_until='domcontentloaded',timeout=30000)
         assert response and response.status==200,(route,'response')
         page.locator('body.sw112-connected').wait_for(timeout=10000)
         assert page.locator('body').get_attribute('data-page')==name
         assert page.locator('main#main-content').count()==1
         assert page.locator('a[href="#main-content"]').count()==1
         assert page.locator('link[href*="workspace-navigation-v112.css"]').count()==1
         assert page.locator('header nav[aria-label="Main navigation"] > a[href="terminal.html"]').count()==1
         assert page.locator('header nav[aria-label="Main navigation"] > a[href="stocks.html"]').count()==1
         assert page.locator('header nav[aria-label="Main navigation"] > a[href="search.html"]').count()==1
         assert page.locator('header nav[aria-label="Main navigation"] > a[href="data-products.html"]').count()==1
         if route!='welcome.html':
          assert page.locator('header nav[aria-label="Main navigation"] > a.sw112-active[aria-current="page"]').get_attribute('href')==route
         else:
          assert page.locator('header a.brand[aria-current="page"]').count()==1
         assert page.locator('.sw-mobile-drawer a[href="search.html"]').count()==1
         assert page.locator('.sw-mobile-drawer a[href="data-products.html"]').count()==1
         assert page.locator('.sw-mobile-drawer a.active[aria-current="page"]').get_attribute('href')==route
         assert page.evaluate('getComputedStyle(document.querySelector("header>a.brand")).backgroundImage')=='none'
         assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'),(route,width,theme)
         assert page.locator('body').get_attribute('data-theme')==theme,(route,theme)
         assert not errors,(route,width,theme,errors)
         if width<=1050:
          assert page.locator('.sw-mobile-nav').is_visible()
          details=page.locator('.sw-mobile-more')
          details.locator('summary').click()
          assert details.get_attribute('open') is not None
          assert details.locator('a[href="data-products.html"]').is_visible()
         else:
          details=page.locator('header .sw-brand-more')
          assert details.is_visible()
          details.locator('summary').click()
          assert details.get_attribute('open') is not None
          assert details.locator('a[href="search.html"]').is_visible()
         details.locator('summary').press('Escape')
         assert details.get_attribute('open') is None,(route,width,'escape')
         if width in (390,1440) and theme=='dark':
          out=ROOT/'workspace-previews';out.mkdir(exist_ok=True)
          page.screenshot(path=str(out/('v112-'+name+'-'+str(width)+'.png')),
              animations='disabled')
         results.append((route,width,theme))
        finally:page.close()
      finally:context.close()
   finally:browser.close()
 finally:server.shutdown();server.server_close()
 assert len(results)==len(ROUTES)*len(WIDTHS)*2
 print(json.dumps({'v112':'pass','routes':len(ROUTES),'views':len(results),'widths':WIDTHS}))

if __name__=='__main__':main()
