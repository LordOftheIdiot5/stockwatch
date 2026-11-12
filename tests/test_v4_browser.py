import json
import re
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
PREV=ROOT/'preview'
FILES={'data/signals.json','data/context.json','watchlist.json','data/freight-routes.json','data/news-archive.json','data/news-latest.json','data/events.json','data/source-health.json','data/fundamentals.json'}
payload={p:json.loads((PREV/p).read_text()) for p in FILES if (PREV/p).exists()}

def load(page,name):
    html=(PREV/name).read_text();html=re.sub(r'<link[^>]*>', '', html);html=re.sub(r'<script[^>]*src=[^>]*></script>', '', html);page.set_content(html,wait_until='domcontentloaded',timeout=10000)
    if name in ['news.html','compare.html','calendar.html','health.html']:page.add_style_tag(content=(PREV/'research.css').read_text())
    page.add_style_tag(content=(PREV/'v4.css').read_text())
    page.evaluate('window.__DATA='+json.dumps(payload))
    page.evaluate('window.fetch=(path)=>{const k=String(path).split("?")[0];const d=window.__DATA[k];return Promise.resolve({ok:d!=null,status:d!=null?200:404,json:async()=>d})}',)
    page.add_script_tag(content=(PREV/'v4.js').read_text())
    if name in ['news.html','compare.html','calendar.html','health.html']:
        page.add_script_tag(content=(PREV/'research.js').read_text())
    page.wait_for_timeout(250)

def main():
 with sync_playwright() as p:
  b=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  for width,height,name in [(1440,950,'index.html'),(390,844,'index.html'),(1440,900,'stocks.html'),(1440,900,'shipping.html'),(1440,900,'spreads.html'),(1440,900,'news.html'),(390,844,'news.html'),(1440,900,'compare.html'),(1440,900,'calendar.html'),(1440,900,'health.html'),(1440,900,'shorts.html'),(1440,900,'commodities.html')]:
   pg=b.new_page(viewport={'width':width,'height':height},device_scale_factor=1)
   pg.add_init_script('window.__DATA='+json.dumps(payload))
   errs=[];pg.on('pageerror',lambda e:errs.append(str(e)))
   load(pg,name)
   txt=pg.locator('#v4app').inner_text() if pg.locator('#v4app').count() else pg.locator('#app').inner_text()
   print(name,width,'content',len(txt),'errors',errs[:2])
   if name=='index.html':
       assert pg.locator('.sw-module').count()==9,txt[:1000]
       if width==1440:pg.screenshot(path=str(ROOT/'home-desktop.png'),full_page=True)
       else:pg.screenshot(path=str(ROOT/'home-mobile.png'),full_page=True)
   if name=='stocks.html':
       assert pg.locator('#stocksRows tr').count()==30
       pg.locator('#stkSearch').fill('Ottobock');assert pg.locator('#stocksRows tr').count()==1
       pg.screenshot(path=str(ROOT/'stocks-desktop.png'),full_page=True)
   if name=='shipping.html':
       assert pg.locator('.sw-route').count()>10
       pg.locator('[data-category="Tankers"]').click();assert pg.locator('.sw-route').count()>1
       pg.screenshot(path=str(ROOT/'shipping-desktop.png'),full_page=True)
   if name=='spreads.html':
       assert pg.locator('#spreadPairs button').count()>5
       pg.screenshot(path=str(ROOT/'spreads-desktop.png'),full_page=True)
   if name=='news.html':
       assert pg.locator('.news-day').count()>=1,txt[:1000]
       if width==1440:pg.screenshot(path=str(ROOT/'news-desktop.png'),full_page=True)
   if errs:raise AssertionError((name,errs))
   pg.close()
  b.close()
 print('Browser checks passed')
if __name__=='__main__':main()
