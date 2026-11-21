"""V116: identify responsible 320px News horizontal overflow; strict no-overflow gate."""
import functools,http.server,json,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as p:
   b=p.chromium.launch(headless=True,args=['--no-sandbox'])
   for theme in ('dark','light'):
    page=b.new_page(viewport={'width':320,'height':740})
    page.add_init_script('localStorage.setItem("stockwatch-theme",'+json.dumps(theme)+')')
    try:
     page.goto('http://127.0.0.1:'+str(server.server_port)+'/news.html',wait_until='domcontentloaded',timeout=30000)
     page.locator('h1').wait_for(timeout=30000);page.wait_for_timeout(120)
     metric=page.evaluate("""() => {
       const w=innerWidth;
       const nodes=[...document.querySelectorAll('body *')].map(e=>{
         const r=e.getBoundingClientRect(),s=getComputedStyle(e);
         return {tag:e.tagName.toLowerCase(),id:e.id,cls:typeof e.className==='string'?e.className.slice(0,100):'',
           text:(e.textContent||'').trim().slice(0,65),
           left:Math.round(r.left*10)/10,right:Math.round(r.right*10)/10,width:Math.round(r.width*10)/10,
           scrollWidth:e.scrollWidth,overflowX:s.overflowX,position:s.position,
           minWidth:s.minWidth,maxWidth:s.maxWidth};
       }).filter(x=>x.right>w+2&&x.left<w&&x.width>0);
       return {viewport:w,scrollWidth:document.documentElement.scrollWidth,
         offenders:nodes.sort((a,b)=>b.right-a.right).slice(0,35)};
     }""")
     print(json.dumps({'theme':theme,'metric':metric}),flush=True)
     assert metric['scrollWidth']<=320+3,metric
     details=page.locator('.sw-mobile-more')
     details.locator('summary').click()
     assert details.get_attribute('open') is not None
     panel=details.locator('.sw-mobile-drawer').bounding_box()
     assert panel and panel['x']>=0 and panel['x']+panel['width']<=321,(theme,panel)
     assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3')
     details.locator('summary').press('Escape')
    finally:page.close()
   b.close()
 finally:server.shutdown();server.server_close()
if __name__=='__main__':main()
