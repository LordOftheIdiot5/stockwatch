"""V117t: Norway/EU source-linked maritime indicators + private-data-safe NavProfit contract math."""
import functools,http.server,json,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def run():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
    functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 results=[]
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
   try:
    for width in (320,390,768,1024,1440,1672,1920):
     for theme in ('dark','light'):
      page=browser.new_page(viewport={'width':width,'height':941},reduced_motion='reduce')
      page.add_init_script('localStorage.setItem("stockwatch-theme",'+json.dumps(theme)+')')
      errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
      try:
       response=page.goto(f'http://127.0.0.1:{server.server_port}/shipping.html',wait_until='domcontentloaded',timeout=30000)
       assert response and response.status==200
       region=page.locator('#nordicMaritime');region.wait_for(timeout=30000)
       cards=page.locator('#nordicCards .sw-nordic-card')
       cards.first.wait_for(timeout=30000)
       assert cards.count()==4,(width,theme)
       assert 'Norway' in cards.nth(0).inner_text()
       assert '2026-Q2' in cards.nth(0).inner_text()
       assert 'Sweden' in cards.nth(1).inner_text()
       assert 'EU-27' in cards.nth(2).inner_text() and '2026-Q1' in cards.nth(2).inner_text()
       assert '862,983' in cards.nth(3).inner_text()
       assert '2024' in cards.nth(3).inner_text()
       assert 'Eurostat archive checked' in page.locator('#nordicStatus').inner_text()
       assert page.locator('a[href*="ssb.no/en/statbank1/table/09518"]').count()==1
       assert page.locator('#nordicMaritime a[href*="kystdatahuset"]').count()==1
       assert page.locator('#nordicMaritime a[href*="mar_go_qmc"]').count()==1
       table=region.locator('details')
       table.locator('summary').focus()
       page.keyboard.press('Enter')
       assert table.evaluate('(e)=>e.open')
       assert region.locator('#nordicRows tr').count()>=5
       assert '1,161' in region.locator('#nordicRows').inner_text()
       assert page.locator('#roroMarketTraffic').count()==1
       assert page.locator('#offshoreRates').count()==1
       assert page.locator('#usdaRouteRates').count()==1
       econ=page.locator('#navprofitEconomics');econ.wait_for(timeout=30000)
       econ.locator('.sw-osv-details summary').focus()
       page.keyboard.press('Enter')
       assert econ.locator('.sw-osv-details').evaluate('(e)=>e.open')
       select=econ.locator('#osvEconBasis')
       assert select.locator('option').count()>=10,(width,theme)
       rate=econ.locator('#osvEconRate')
       assert float(rate.input_value())>0
       assert 'Q3' in econ.locator('#osvEconCitation').inner_text()
       assert econ.locator('#osvEconCitation a[href^="https://"]').count()==1
       econ.locator('#osvEconForm button[type="submit"]').click()
       result=econ.locator('#osvEconResults')
       assert 'operating contribution' in result.inner_text().lower()
       assert 'Break-even dayrate' in result.inner_text()
       assert 'not' in result.inner_text().lower()
       assert '$' in result.inner_text()
       econ.locator('#osv_billableDays').fill('90')
       econ.locator('#osvEconForm button[type="submit"]').click()
       assert 'cannot exceed service days' in result.inner_text()
       econ.locator('#osv_billableDays').fill('25')
       assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3'),(width,theme)
       assert not errors,(width,theme,errors)
       if theme=='dark' and width in (390,1672):
        table.locator('summary').focus();page.keyboard.press('Enter')
        econ.locator('.sw-osv-details summary').focus();page.keyboard.press('Enter')
        page.evaluate('scrollTo(0,0)');page.wait_for_timeout(90)
        out=ROOT/'workspace-previews'/f'shipping-region-v117t-firstfold-{width}.png'
        out.parent.mkdir(exist_ok=True);page.screenshot(path=str(out),animations='disabled')
       results.append({'width':width,'theme':theme,'regions':cards.count(),'source':True,'scenario':True})
      finally:page.close()
    # Validate source-failure isolation: prior official price cards still work.
    fail=browser.new_page(viewport={'width':390,'height':800})
    fail.route('**/data/shipping-roro-traffic.json',lambda route:route.abort())
    fail.goto(f'http://127.0.0.1:{server.server_port}/shipping.html',wait_until='domcontentloaded',timeout=30000)
    fail.locator('#nordicMaritime').wait_for(timeout=30000)
    fail.locator('#nordicStatus').get_by_text('temporarily unavailable',exact=False).wait_for(timeout=30000)
    fail.locator('.sw-offshore-card').first.wait_for(timeout=30000)
    assert fail.locator('#usdaRateCards .sw-usda-card').count()==2
    fail.close()
   finally:browser.close()
 finally:server.shutdown();server.server_close()
 assert len(results)==14
 print(json.dumps({'v117t':'passed','views':results,'region_failure':'passed'}))

if __name__=='__main__':run()
