"""V119: owner-approved map-first Shipping UI, preserved real research, semantics and fallbacks."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import functools, http.server, threading, json
ROOT=Path(__file__).resolve().parents[1]
VIEWS=(320,390,768,1024,1440,1672,1920)
def main():
 server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 done=[]
 try:
  with sync_playwright() as pw:
   browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
   try:
    for width in VIEWS:
     for theme in ('dark','light'):
      page=browser.new_page(viewport={'width':width,'height':940},reduced_motion='reduce')
      page.add_init_script('localStorage.setItem("stockwatch-theme",'+json.dumps(theme)+')')
      errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
      try:
       resp=page.goto('http://127.0.0.1:'+str(server.server_port)+'/shipping.html',wait_until='domcontentloaded',timeout=30000)
       assert resp and resp.status==200
       map=page.locator('#shippingWorldMap.sw119-mapfirst')
       map.wait_for(timeout=30000)
       page.locator('#shippingMapPins .sw-atlas-point').first.wait_for(timeout=30000)
       top=page.locator('#sw119Topbar')
       assert top.is_visible()
       assert 'Maritime Atlas' in top.inner_text()
       assert page.locator('.sw-content > .sw-page-head').count()==1
       assert not page.locator('.sw-content > .sw-page-head').is_visible()
       assert page.locator('.sw-side').count()==1 and not page.locator('.sw-side').is_visible()
       bbox=map.bounding_box()
       assert bbox and bbox['height'] >=620,(width,theme,bbox)
       assert bbox['y'] <=75,(width,theme,bbox)
       assert bbox['width']>=width-6,(width,theme,bbox)
       assert page.locator('#shippingMapPins .sw-atlas-point').count()==40
       assert page.locator('#sw119MaritimeGrid line').count()==8
       page.locator('#sw119MaritimeBorders path').first.wait_for(timeout=30000)
       assert page.locator('#sw119MaritimeBorders path').count()>=100
       assert 'One map. Every maritime market.' in page.locator('#shippingAtlasTitle').inner_text()
       assert page.locator('.sw119-topbar a[href="index.html"]').count()==2
       assert page.locator('#sw119OffshoreRateLink[href="#offshoreRates"]').count()==1
       assert page.locator('#sw119ResearchIntro a[href="#navprofitEconomics"]').count()==1
       assert page.locator('#sw119ResearchIntro a[href="#voyageEstimator"]').count()==1
       assert page.locator('#sw119ResearchMenu').count()==1
       page.locator('#sw119ResearchMenu summary').click()
       assert page.locator('#sw119ResearchMenu').evaluate('(e)=>e.open')
       assert page.locator('#sw119ResearchMenu a[href="#routeCompare"]').count()==1
       page.locator('#sw119ResearchMenu summary').click()
       assert page.locator('#offshoreRates .sw-offshore-card').count()==4
       assert page.locator('#usdaRateCards .sw-usda-card').count()==2
       assert page.locator('#nordicMaritime').count()==1
       assert page.locator('#navprofitEconomics').count()==1
       assert page.locator('#worldBankPortTraffic').count()==1
       assert page.locator('#routeCompare').count()==1
       assert page.locator('#voyageEstimator').count()==1
       assert page.locator('#shippingDataGuide').count()==1
       assert not map.locator('#shippingDataGuide').count()
       # Select Rotterdam, but show only Netherlands country totals, not fictitious Rotterdam TEUs.
       page.locator('#shippingMapPick').select_option('NL-RTM')
       detail=page.locator('#shippingMapInspector')
       if width<=900: assert detail.is_visible()
       assert 'Rotterdam' in page.locator('#shippingMapDetailTitle').inner_text()
       stat=page.locator('#sw119DetailActions .sw119-country-context')
       stat.wait_for(timeout=30000)
       assert '14,517,179' in stat.inner_text()
       assert 'country total' in stat.inner_text().lower()
       assert 'NOT the selected port alone' in stat.inner_text()
       assert page.locator('#sw119DetailActions a[href="#worldBankPortTraffic"]').count()==1
       # Research CTA selection changes with actual layer and source.
       page.locator('[data-layer="lanes"]').click()
       page.locator('#shippingMapPick').select_option('us-gulf-japan-grain-2026-11-12')
       assert '$72.75' in page.locator('#shippingMapFact').inner_text()
       assert '2026-11-12' in page.locator('#shippingMapFact').inner_text()
       assert page.locator('#sw119DetailActions a[href="#voyageEstimator"]').count()==1
       page.locator('[data-layer="ais"]').click()
       assert '0 verified vessel positions' in page.locator('#shippingMapCount').inner_text()
       assert page.locator('#shippingMapPins .sw-atlas-point').count()==0
       assert 'No live AIS feed connected' in page.locator('#shippingMapDetailTitle').inner_text()
       page.locator('[data-layer="ports"]').click()
       page.locator('#shippingMapSearch').fill('Bergen')
       assert page.locator('#shippingMapPins .sw-atlas-point').count()==1
       page.locator('#shippingMapSearch').fill('')
       map_svg=page.locator('#shippingMapSvg')
       before=map_svg.get_attribute('viewBox')
       page.locator('[data-map-zoom="in"]').click()
       assert map_svg.get_attribute('viewBox')!=before
       page.locator('[data-map-zoom="reset"]').click()
       assert map_svg.get_attribute('viewBox')==before
       page.locator('#shippingMapPick').select_option('NL-RTM')
       assert 'Rotterdam' in page.locator('#shippingMapDetailTitle').inner_text()
       page.locator('#sw119InspectorClose').click()
       assert not detail.is_visible()
       page.locator('#shippingMapPick').select_option('NO-BGO')
       assert detail.is_visible()
       assert 'Bergen' in page.locator('#shippingMapDetailTitle').inner_text()
       assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3'),(width,theme,page.evaluate('document.documentElement.scrollWidth'))
       assert not errors,(width,theme,errors)
       if theme=='dark' and width in (390,1672):
        page.locator('#sw119InspectorClose').click() if width==390 else None
        page.evaluate('window.scrollTo(0,0)')
        page.wait_for_timeout(80)
        out=ROOT/'workspace-previews'/f'shipping-mapfirst-v119-{width}.png'
        out.parent.mkdir(exist_ok=True)
        page.screenshot(path=str(out),animations='disabled',timeout=30000)
       done.append({'width':width,'theme':theme,'verified_port_anchors':40,'real_source_borders':True,'research_preserved':True})
      finally:page.close()
    # Missing border data retains functional world land and port research.
    page=browser.new_page(viewport={'width':390,'height':840})
    page.route('**/data/shipping-world-borders-v119.json',lambda route:route.abort())
    page.goto('http://127.0.0.1:'+str(server.server_port)+'/shipping.html',wait_until='domcontentloaded',timeout=30000)
    page.locator('#shippingMapPins .sw-atlas-point').first.wait_for(timeout=30000)
    assert page.locator('#shippingMapPins .sw-atlas-point').count()==40
    assert page.locator('#shippingMapSvg image[href="brand/world-land-ne110.svg"]').count()==1
    assert page.locator('#offshoreRates .sw-offshore-card').count()==4
    page.close()
   finally:browser.close()
 finally:server.shutdown();server.server_close()
 assert len(done)==14
 print(json.dumps({'status':'PASS','matrix':done,'border_data_fallback':'PASS'},indent=2))
if __name__=='__main__':main()
