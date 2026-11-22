"""Shipping S1 — independently sourced issuer rate, filtering, and fallback UX."""
import functools
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]

def main():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
  functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 evidence=[]
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
   try:
    for width in (320,390,768,1024,1440,1672,1920):
     for theme in ('dark','light'):
      page=browser.new_page(viewport={'width':width,'height':941},reduced_motion='reduce')
      page.add_init_script('localStorage.setItem("stockwatch-theme",'+json.dumps(theme)+')')
      errs=[];page.on('pageerror',lambda e:errs.append(str(e)))
      try:
       response=page.goto(f'http://127.0.0.1:{server.server_port}/shipping.html',
        wait_until='domcontentloaded',timeout=30000)
       panel=page.locator('#offshoreRates');panel.wait_for(timeout=30000)
       page.locator('.sw-offshore-card').first.wait_for(timeout=30000)
       assert response and response.status==200
       assert panel.get_attribute('aria-labelledby')=='offshoreRatesTitle'
       assert '11 published Q3 2026 class averages' in page.locator('#offshoreStatus').inner_text()
       assert '0 licensed daily spot quotes' in page.locator('#offshoreStatus').inner_text()
       cards=page.locator('.sw-offshore-card')
       assert cards.count()==4,(width,theme,cards.count())
       assert '$34,153' in cards.nth(0).inner_text()
       assert '$35,392' in cards.nth(1).inner_text()
       assert '$28,052' in cards.nth(2).inner_text()
       assert '$403,113' in cards.nth(3).inner_text()
       assert page.locator('#offshoreBody tr').count()==11
       assert page.locator('#offshoreBody a[href^="https://"]').count()==11
       page.locator('#usdaRateCards .sw-usda-card').first.wait_for(timeout=30000)
       assert page.locator('#usdaRateCards .sw-usda-card').count()==2
       assert '$72.75' in page.locator('#usdaRateCards').inner_text()
       assert '$39.50' in page.locator('#usdaRateCards').inner_text()
       assert '/ metric tonne' in page.locator('#usdaRateCards').inner_text()
       assert '2026-11-12' in page.locator('#usdaRateStatus').inner_text()
       assert page.locator('#usdaRateCards a[href*="ams.usda.gov"]').count()==2
       assert page.locator('#shippingBenchmarkAnchor').count()==1
       assert page.locator('#routeGrid').count()==1
       assert page.locator('#voyageEstimator').count()==1
       assert page.locator('#offshoreCompare').is_checked()
       assert 'vs $' in page.locator('#offshoreBody').inner_text()
       page.locator('#offshoreSegment').select_option('Rigs')
       assert page.locator('#offshoreBody tr').count()==2
       assert '$403,113' in page.locator('#offshoreBody').inner_text()
       assert '$207,651' in page.locator('#offshoreBody').inner_text()
       page.locator('#offshoreIssuer').select_option('tdw2026q3')
       assert 'No company-reported rates match' in page.locator('#offshoreBody').inner_text()
       page.locator('#offshoreIssuer').select_option('all')
       page.locator('#offshoreSegment').select_option('all')
       page.locator('#offshoreSearch').fill('AHTS')
       assert page.locator('#offshoreBody tr').count()==3
       page.locator('#offshoreSearch').fill('')
       page.locator('#offshoreCompare').uncheck()
       assert 'vs $' not in page.locator('#offshoreBody').inner_text()
       page.locator('#offshoreCompare').check()
       details=page.locator('.sw-offshore-explain')
       details.locator('summary').focus()
       page.keyboard.press('Enter')
       assert details.evaluate('(e)=>e.open')
       assert 'broker' in details.inner_text().lower()
       assert 'spot' in details.inner_text().lower()
       assert 'spot' in details.inner_text().lower()
       assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3'),(width,theme,page.evaluate('document.documentElement.scrollWidth'))
       assert not errs,(width,theme,errs)
       # A screenshot scrolled to an opened explanation is NOT a first-fold audit.
       # Return to actual page top before measuring geometry and capturing evidence.
       page.evaluate('window.scrollTo(0,0)')
       page.wait_for_timeout(80)
       assert page.evaluate('window.scrollY')==0
       firstfold_top=round(panel.bounding_box()['y'])
       first_price_top=round(cards.first.bounding_box()['y'])
       if width in (390,1672):
        # Price visibility is now a desktop/mobile first-screen acceptance gate.
        assert firstfold_top<540,(width,theme,firstfold_top)
        assert first_price_top<930,(width,theme,first_price_top)
       if theme=='dark' and width in (390,1672):
        path=ROOT/'workspace-previews'/f'shipping-s1-firstfold-{width}.png'
        path.parent.mkdir(exist_ok=True)
        page.screenshot(path=str(path),animations='disabled')
       evidence.append({'width':width,'theme':theme,
        'rates':page.locator('#offshoreBody tr').count(),
        'rateTop':firstfold_top,
        'pageWidth':page.evaluate('document.documentElement.scrollWidth')})
      finally:page.close()
    fail=browser.new_page(viewport={'width':390,'height':840})
    fail.route('**/data/offshore-rate-evidence-v117s.json',lambda route:route.abort())
    fail.goto(f'http://127.0.0.1:{server.server_port}/shipping.html',wait_until='domcontentloaded',timeout=30000)
    fail.locator('#offshoreRates').wait_for(timeout=30000)
    fail.locator('.sw-offshore-error').wait_for(timeout=30000)
    assert 'temporarily unavailable' in fail.locator('#offshoreStatus').inner_text()
    assert fail.locator('#shippingBenchmarkAnchor').count()==1
    assert fail.locator('#routeGrid').count()==1
    fail.locator('#usdaRateCards .sw-usda-card').first.wait_for(timeout=30000)
    assert fail.locator('#usdaRateCards .sw-usda-card').count()==2
    fail.close()
    usda_fail=browser.new_page(viewport={'width':390,'height':840})
    usda_fail.route('**/data/shipping-usda-ocean-rates-s1.json',lambda route:route.abort())
    usda_fail.goto(f'http://127.0.0.1:{server.server_port}/shipping.html',wait_until='domcontentloaded',timeout=30000)
    usda_fail.locator('#usdaRouteRates').wait_for(timeout=30000)
    usda_fail.locator('#usdaRateStatus').get_by_text('snapshot unavailable',exact=False).wait_for(timeout=30000)
    assert usda_fail.locator('.sw-offshore-card').count()==4
    assert usda_fail.locator('#routeGrid').count()==1
    usda_fail.close()
   finally:browser.close()
 finally:server.shutdown();server.server_close()
 assert len(evidence)==14
 print(json.dumps({'shipping_s1':'passed','views':evidence,'failed_source_fallback':'passed'},indent=2))

if __name__=='__main__':
 main()
