"""V110a real browser contract — approved design layout and honest heatmap states."""
import functools,http.server,threading,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def main():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
     functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 results=[]
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
   for width in (320,390,768,1024,1440,1920):
    for theme in ('dark','light'):
     page=browser.new_page(viewport={'width':width,'height':900})
     page.add_init_script("localStorage.setItem('stockwatch-theme',"+json.dumps(theme)+")")
     errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
     page.goto(f'http://127.0.0.1:{server.server_port}/index.html',
       wait_until='domcontentloaded',timeout=30000)
     page.locator('#overviewMacroSeries').wait_for(timeout=30000)
     control=page.locator('#workspaceCoverage')
     assert control.input_value()=='observed'
     heat=page.locator('.sw98-market-secondary .sw-ws-heatmap')
     companion=page.locator('.sw98-market-secondary .sw110-heat-companion')
     movers=companion.locator('.sw-panel').first
     watch=companion.locator('#overviewWatchlist')
     assert all(x.count()==1 for x in (heat,companion,movers,watch))
     assert 'No saved companies yet' in watch.inner_text()
     assert page.locator('.sw98-intelligence-rail .sw-overview-news').count()==1
     assert page.locator('#globalMarketPulse').count()==1
     assert 'Taiwan sources connected' in page.locator('#globalMarketPulse').inner_text()
     assert 'session-verified' in page.locator('details.sw96-source-status').inner_text()
     first_count=page.locator('#workspaceHeatCount').inner_text()
     assert 'dated changes' in first_count and 'price-only' in first_count
     # The default never quietly hides price-only/missing records: user can see counts
     # and explicitly switch filters.
     control.select_option('priced')
     assert control.input_value()=='priced'
     all_count=page.locator('#workspaceHeatCount').inner_text()
     assert 'price-only' in all_count
     control.select_option('missing')
     assert control.input_value()=='missing'
     control.select_option('observed')
     assert page.locator('#workspaceHeatCount').inner_text()==first_count
     chart=page.locator('.sw98-primary .sw92-focus-chart')
     rail=page.locator('.sw98-intelligence-rail')
     assert chart.bounding_box()['y'] < heat.bounding_box()['y']
     if width>=1320:
      # V110b uses CSS display:contents to put real movers and watchlist
      # alongside the heatmap as independent columns. The wrapper has no box.
      panels=companion.locator(':scope > .sw-panel')
      assert panels.count()==2
      for i in range(2):
       assert abs(heat.bounding_box()['y']-panels.nth(i).bounding_box()['y'])<6
     elif width>=1200:
      assert abs(heat.bounding_box()['y']-companion.bounding_box()['y'])<6
     else:
      assert companion.bounding_box()['y']>=heat.bounding_box()['y']
     if width>=1320:
      breadth=page.locator('.sw98-primary .sw92-focus-summary')
      news=page.locator('.sw98-primary .sw-overview-news')
      assert abs(chart.bounding_box()['y']-breadth.bounding_box()['y'])<6
      assert abs(chart.bounding_box()['y']-news.bounding_box()['y'])<6
      assert chart.bounding_box()['width']>breadth.bounding_box()['width']
     elif width>=1200:
      assert chart.bounding_box()['width']>rail.bounding_box()['width']
     if width>=1200:
      assert chart.bounding_box()['height']<630
     assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+2'),width
     assert not errors,errors
     if width in (390,1440,1920) and theme=='dark':
      (ROOT/'workspace-previews').mkdir(exist_ok=True)
      page.screenshot(path=str(ROOT/'workspace-previews'/f'v110-overview-{width}.png'),
        animations='disabled')
     results.append({'width':width,'theme':theme,'heatmap':first_count,
       'chartHeight':round(chart.bounding_box()['height'])})
     page.close()
   browser.close()
 finally:
  server.shutdown();server.server_close()
 print(json.dumps({'v110a':'accepted','views':len(results),'coverage':results[0]['heatmap']}))
if __name__=='__main__':main()
