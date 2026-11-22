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
     coverage=page.locator('.sw98-market-secondary .sw110d-market-coverage')
     coverage.locator('.sw110d-coverage-total strong').wait_for(timeout=10000)
     movers=page.locator('.sw110d-movers .sw-panel')
     watch=companion.locator('#overviewWatchlist')
     assert all(x.count()==1 for x in (heat,companion,coverage,movers,watch))
     assert 'NOT market returns' in coverage.inner_text()
     assert ' / ' in coverage.locator('.sw110d-coverage-total strong').inner_text()
     coverage.locator('.sw110e-world').wait_for(timeout=10000)
     assert coverage.locator('.sw110e-world img[src$="world-land-ne110.svg"]').count()==1
     assert coverage.locator('.sw110e-pin').count()==2
     assert 'market movement' in coverage.locator('.sw110e-pin').first.get_attribute('aria-label')
     coverage.locator('.sw110e-all-venues summary').click()
     assert coverage.locator('.sw110d-venue').count()>=6
     coverage.locator('.sw110e-all-venues summary').click()
     assert page.locator('.sw110d-movers').get_attribute('open') is None
     page.locator('.sw110d-movers summary').click()
     assert movers.is_visible()
     page.locator('.sw110d-movers summary').click()
     assert 'No saved companies yet' in watch.inner_text()
     assert page.locator('.sw98-intelligence-rail .sw-overview-news').count()==1
     assert page.locator('#globalMarketPulse').count()==1
     assert 'Taiwan sources connected' in page.locator('#globalMarketPulse').inner_text()
     assert 'date-comparable' in page.locator('details.sw96-source-status').inner_text()
     assert 'session-verified' not in page.locator('details.sw96-source-status').inner_text()
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
      # V116c: exchange coverage + watchlist directly follow snapshot + news,
      # using the blank area seen in owner screenshots. Heatmap spans all columns.
      box=heat.bounding_box()
      cov=coverage.bounding_box()
      saved=watch.bounding_box()
      assert abs(cov['y']-saved['y'])<8,(width,cov,saved)
      assert box['width']>chart.bounding_box()['width']*1.9,(width,box)
      assert 0<=box['y']-max(chart.bounding_box()['y']+chart.bounding_box()['height'],
          cov['y']+cov['height'],saved['y']+saved['height'])<=18
      assert chart.bounding_box()['height']>240
      # Enlarged map must remain full width and reversible, including the
      # real selected-company inspector (not a blank right-hand column).
      toggle=page.locator('#workspaceHeatExpand')
      toggle.click()
      assert page.locator('#workspaceHeatmap.sw-heat-expanded').count()==1
      assert abs(heat.bounding_box()['width']-box['width'])<10
      assert page.locator('.sw93-heat-inspector').first.bounding_box()['width']>chart.bounding_box()['width']*1.7
      toggle.click()
      assert page.locator('#workspaceHeatmap.sw-heat-expanded').count()==0
     elif width>=900:
      assert abs(heat.bounding_box()['y']-coverage.bounding_box()['y'])<6
      assert watch.bounding_box()['y']>=coverage.bounding_box()['y']
     else:
      assert coverage.bounding_box()['y']>=heat.bounding_box()['y']
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
