"""V118: independent 14-view map, data explanation, controls, AIS absence and source failover."""
import functools
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
WIDTHS=(320,390,768,1024,1440,1672,1920)
def main():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
  functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 outcomes=[]
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
   try:
    for width in WIDTHS:
     for theme in ('dark','light'):
      page=browser.new_page(viewport={'width':width,'height':940},reduced_motion='reduce')
      page.add_init_script('localStorage.setItem("stockwatch-theme",'+json.dumps(theme)+')')
      errors=[]
      page.on('pageerror',lambda e:errors.append(str(e)))
      try:
       response=page.goto('http://127.0.0.1:'+str(server.server_port)+'/shipping.html',
        wait_until='domcontentloaded',timeout=30000)
       assert response and response.status==200
       atlas=page.locator('#shippingWorldMap');atlas.wait_for(timeout=30000)
       page.locator('#shippingMapPins .sw-atlas-point').first.wait_for(timeout=30000)
       assert page.locator('#shippingMapPins .sw-atlas-point').count()==40,(width,theme)
       assert page.locator('#shippingMapCount').inner_text().startswith('40 map observations')
       assert page.locator('#shippingMapSvg image[href="brand/world-land-ne110.svg"]').count()==1
       assert page.locator('#shippingMapSvg').get_attribute('viewBox')=='0 0 900 388'
       # Accessible observation selector is an alternative to interacting with tiny points.
       select=page.locator('#shippingMapPick')
       assert select.locator('option').count()==41
       select.select_option('NO-BGO')
       assert 'Bergen' in page.locator('#shippingMapDetailTitle').inner_text()
       assert 'No market observation' in page.locator('#shippingMapFact').inner_text()
       assert 'approximate' in page.locator('#shippingMapFact').inner_text()
       assert page.locator('#shippingMapFact a[href^="https://"]').count()==1
       # North Sea filter contains Norwegian and European reference ports, not Asia.
       page.locator('#shippingMapRegion').select_option('nordic')
       assert page.locator('#shippingMapPins .sw-atlas-point').count()<40
       assert page.locator('#shippingMapPins .sw-atlas-point').count()>=10
       page.locator('#shippingMapSearch').fill('Bergen')
       assert page.locator('#shippingMapPins .sw-atlas-point').count()==1
       page.locator('#shippingMapSearch').fill('')
       page.locator('#shippingMapRegion').select_option('global')
       # Source-dated annual *country* container TEU, not Singapore port traffic.
       page.locator('[data-layer="containers"]').click()
       page.locator('#shippingMapPins .sw-atlas-point').first.wait_for(timeout=30000)
       assert page.locator('#shippingMapPins .sw-atlas-point').count()>=14
       page.locator('#shippingMapPick').select_option('container:NOR')
       assert '862,983' in page.locator('#shippingMapFact').inner_text()
       assert '2024' in page.locator('#shippingMapFact').inner_text()
       assert 'Annual country aggregate' in page.locator('#shippingMapFact').inner_text()
       assert 'World Bank' in page.locator('#shippingMapSourceStatus').inner_text()
       # Same-country Eurostat quarterly Ro-Ro source and different regional periods.
       page.locator('[data-layer="roro"]').click()
       page.locator('#shippingMapPick').select_option('roro:NO')
       assert '1,161' in page.locator('#shippingMapFact').inner_text()
       assert '2026-Q2' in page.locator('#shippingMapFact').inner_text()
       page.locator('#shippingMapPick').select_option('roro:EU27_2020')
       assert '2026-Q1' in page.locator('#shippingMapFact').inner_text()
       assert 'never sum' in page.locator('#shippingMapFact').inner_text()
       # Liner connectivity is index, not real freight or delivered demand.
       page.locator('[data-layer="connectivity"]').click()
       page.locator('#shippingMapPick').select_option('liner:Norway')
       assert 'LSCI index' in page.locator('#shippingMapFact').inner_text()
       assert '2026-09' in page.locator('#shippingMapFact').inner_text()
       assert 'Network integration index' in page.locator('#shippingMapFact').inner_text()
       # Two USDA price-bearing schematic lanes only, never actual sailed routes.
       page.locator('[data-layer="lanes"]').click()
       assert page.locator('#shippingMapPins .sw-atlas-point').count()==2
       assert page.locator('#shippingMapLines .sw-atlas-lane').count()==6
       page.locator('#shippingMapPick').select_option('us-gulf-japan-grain-2026-11-12')
       assert '$72.75' in page.locator('#shippingMapFact').inner_text()
       assert '2026-11-12' in page.locator('#shippingMapFact').inner_text()
       assert 'Schematic origin' in page.locator('#shippingMapFact').inner_text()
       # Ships layer refuses to hallucinate positions.
       page.locator('[data-layer="ais"]').click()
       assert page.locator('#shippingMapPins .sw-atlas-point').count()==0
       assert '0 verified vessel positions' in page.locator('#shippingMapCount').inner_text()
       assert 'No live AIS feed connected' in page.locator('#shippingMapDetailTitle').inner_text()
       assert '0' in page.locator('#shippingMapSourceStatus').inner_text()
       assert page.locator('#shippingWorldMap a[href*="kystverket.no"]').count()==1
       # Close the responsive AIS sheet before the underlying camera buttons;
       # the sheet correctly intercepts map input until dismissed.
       page.locator('#sw119InspectorClose').click()
       assert not page.locator('#shippingMapInspector').is_visible()
       # Keyboard map zoom and Home reset.
       map_svg=page.locator('#shippingMapSvg')
       map_svg.focus();page.keyboard.press('+')
       assert map_svg.get_attribute('viewBox')!='0 0 900 388'
       map_svg.focus();page.keyboard.press('ArrowRight')
       page.locator('[data-map-zoom="reset"]').click()
       assert map_svg.get_attribute('viewBox')=='0 0 900 388'
       page.locator('[data-map-zoom="in"]').click()
       assert map_svg.get_attribute('viewBox')!='0 0 900 388'
       page.locator('[data-map-zoom="out"]').click()
       # Terms and glossary accessible by keyboard.
       guide=page.locator('#shippingDataGuide')
       guide.locator('summary').focus();page.keyboard.press('Enter')
       assert guide.evaluate('(e)=>e.open')
       assert guide.locator('.sw-atlas-glossary article').count()==6
       assert 'TEU' in guide.inner_text() and 'AIS' in guide.inner_text()
       assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3'),(width,theme,page.evaluate('document.documentElement.scrollWidth'))
       assert page.locator('#offshoreRates .sw-offshore-card').count()==4
       assert page.locator('#usdaRateCards .sw-usda-card').count()==2
       assert page.locator('#nordicMaritime').count()==1
       assert page.locator('#navprofitEconomics').count()==1
       assert not errors,(width,theme,errors)
       if theme=='dark' and width in (390,1672):
        page.locator('[data-layer="ports"]').click()
        guide.locator('summary').focus();page.keyboard.press('Enter')
        pic=ROOT/'workspace-previews'/f'shipping-world-map-v118-{width}.png'
        pic.parent.mkdir(exist_ok=True)
        atlas.screenshot(path=str(pic),animations='disabled',timeout=30000)
       outcomes.append({'width':width,'theme':theme,'portPins':40,'realIndicators':'ok','AIS':'no fake ships','overflow':False})
      finally:page.close()
    # A failed activity file can't erase valid world port locators or invent a new value.
    broken=browser.new_page(viewport={'width':390,'height':840})
    broken.route('**/data/shipping-roro-traffic.json',lambda route:route.abort())
    broken.goto('http://127.0.0.1:'+str(server.server_port)+'/shipping.html',wait_until='domcontentloaded',timeout=30000)
    broken.locator('#shippingWorldMap').wait_for(timeout=30000)
    broken.locator('#shippingMapPins .sw-atlas-point').first.wait_for(timeout=30000)
    broken.locator('[data-layer="roro"]').click()
    assert broken.locator('#shippingMapPins .sw-atlas-point').count()==0
    assert 'No measured observations connected' in broken.locator('#shippingMapPick').inner_text()
    broken.locator('[data-layer="containers"]').click()
    assert broken.locator('#shippingMapPins .sw-atlas-point').count()>=14
    broken.close()
    missing=browser.new_page(viewport={'width':390,'height':840})
    missing.route('**/data/shipping-world-atlas-v118.json',lambda route:route.abort())
    missing.goto('http://127.0.0.1:'+str(server.server_port)+'/shipping.html',wait_until='domcontentloaded',timeout=30000)
    missing.locator('#shippingMapCount').get_by_text('temporarily unavailable',exact=False).wait_for(timeout=30000)
    assert missing.locator('#offshoreRates .sw-offshore-card').count()==4
    missing.close()
   finally:browser.close()
 finally:server.shutdown();server.server_close()
 assert len(outcomes)==14
 print(json.dumps({'v118':'passed','screens':outcomes,'source_failover':'passed'},indent=2))

if __name__=='__main__':main()
