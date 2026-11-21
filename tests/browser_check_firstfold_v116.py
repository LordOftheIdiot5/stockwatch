"""V116a: measurable first-fold composition of sourced Overview data.

The approved reference is a compositional target, *not* authorized market data.
This is a structural gate, not a claim of pixel-perfect visual approval.
"""
import functools,http.server,json,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def main():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
  functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 metrics=[]
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
   try:
    for width,threshold in ((1440,855),(1672,880),(1920,930)):
     for theme in ('dark','light'):
      page=browser.new_page(viewport={'width':width,'height':941},
        reduced_motion='reduce',device_scale_factor=1)
      page.add_init_script('localStorage.setItem("stockwatch-theme",'+json.dumps(theme)+')')
      errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
      try:
       page.goto('http://127.0.0.1:'+str(server.server_port)+'/index.html',
         wait_until='domcontentloaded',timeout=30000)
       page.locator('#overviewMacroPlot svg').wait_for(timeout=30000)
       page.locator('.sw110e-world').wait_for(timeout=30000)
       chart=page.locator('.sw98-primary .sw92-focus-chart')
       summary=page.locator('.sw98-primary .sw92-focus-summary')
       news=page.locator('.sw98-primary .sw-overview-news')
       heat=page.locator('.sw98-market-secondary .sw-ws-heatmap')
       coverage=page.locator('.sw98-market-secondary .sw110d-market-coverage')
       watch=page.locator('.sw98-market-secondary .sw99-watchlist')
       box={k:v.bounding_box() for k,v in [('chart',chart),('summary',summary),
         ('news',news),('heat',heat),('coverage',coverage),('watch',watch)]}
       assert all(box.values()),box
       assert abs(box['chart']['y']-box['summary']['y'])<7
       assert abs(box['chart']['y']-box['news']['y'])<7
       assert abs(box['heat']['y']-box['coverage']['y'])<7
       assert abs(box['heat']['y']-box['watch']['y'])<7
       assert box['chart']['width']>box['summary']['width']
       geometry=page.evaluate("""() => {
        const names=['.sw-overview-head','.sw96-source-status','#globalMarketPulse',
          '.sw98-primary','.sw98-primary .sw-overview-chart-controls',
          '.sw98-primary #overviewMacro','.sw98-primary #overviewMacroPlot',
          '.sw98-primary #overviewMacroPlot svg',
          '.sw98-primary .sw-overview-news',
          '.sw98-market-secondary'];
        return Object.fromEntries(names.map(s=>{
         const e=document.querySelector(s),b=e?.getBoundingClientRect();
         return [s,b?{top:Math.round(b.y),height:Math.round(b.height),
           width:Math.round(b.width),display:getComputedStyle(e).display}:null]
        }));
       }""")
       print(json.dumps({'v116Geometry':width,'theme':theme,
         'heatY':box['heat']['y'],'targetY':threshold,
         'components':geometry}),flush=True)
       if theme=='dark':
        out=ROOT/'workspace-previews';out.mkdir(exist_ok=True)
        page.screenshot(path=str(out/f'v116-overview-firstfold-{width}.png'),
          animations='disabled')
       assert box['heat']['y']<=threshold,(width,theme,'heatmap below first-fold target',box['heat']['y'],threshold)
       svg=page.locator('#overviewMacroPlot svg')
       sz=svg.bounding_box()
       assert 2.11<sz['width']/sz['height']<2.36,(width,sz)
       # V116b: the truthful freshness disclosure occupies desktop header
       # whitespace, rather than a separate 35px high row.
       page.locator('.sw-overview-head > details.sw96-source-status').wait_for(timeout=10000)
       assert page.locator('.sw-overview-head > details.sw96-source-status').count()==1
       if width==1440:
        directions=page.locator('.sw98-primary .sw-overview-chart-controls label').evaluate_all(
         '(els)=>els.map(e=>getComputedStyle(e).flexDirection)')
        assert directions==['column','column','column'],directions
       assert 'Taiwan sources connected' in page.locator('#globalMarketPulse').inner_text()
       assert 'not a stock index' in chart.inner_text()
       assert 'NOT market returns' in coverage.inner_text()
       assert 'No saved companies yet' in watch.inner_text()
       assert not errors,errors
       assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3')
       metrics.append({'width':width,'theme':theme,'heatTop':round(box['heat']['y']),
         'chartHeight':round(box['chart']['height']),'chartWidth':round(box['chart']['width']),
         'breadthTop':round(box['summary']['y']),'newsTop':round(box['news']['y'])})
       if theme=='dark':
        out=ROOT/'workspace-previews';out.mkdir(exist_ok=True)
        page.screenshot(path=str(out/f'v116-overview-firstfold-{width}.png'),
          animations='disabled')
      finally:page.close()
   finally:browser.close()
 finally:server.shutdown();server.server_close()
 print(json.dumps({'v116a':'passed','firstfold':metrics},indent=2))

if __name__=='__main__':main()
