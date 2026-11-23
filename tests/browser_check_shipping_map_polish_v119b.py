"""V119b: visual clarity and unobstructed map acceptance, source data unchanged."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import functools, http.server, json, threading

ROOT=Path(__file__).resolve().parents[1]
WIDTHS=(320,390,768,1024,1440,1672,1920)

def run():
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
        functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    summary=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                for width in WIDTHS:
                    for theme in ('dark','light'):
                        page=browser.new_page(viewport={'width':width,'height':940},reduced_motion='reduce')
                        errors=[]
                        page.on('pageerror',lambda e:errors.append(str(e)))
                        page.add_init_script('localStorage.setItem("stockwatch-theme",'+json.dumps(theme)+')')
                        try:
                            resp=page.goto(f'http://127.0.0.1:{server.server_port}/shipping.html',
                                           wait_until='domcontentloaded',timeout=30000)
                            assert resp and resp.status==200
                            page.locator('#shippingMapPins .sw-atlas-point').first.wait_for(timeout=30000)
                            assert page.locator('#shippingMapPins .sw-atlas-point').count()==40
                            assert page.locator('#sw119bFocusSelection').count()==1
                            assert page.locator('.sw119b-presets button').count()==3
                            assert not page.locator('#shippingMapInspector').is_visible(),(width,theme,'panel initially open')
                            assert page.locator('#shippingMapPick').input_value()==''
                            assert page.locator('#shippingWorldMap').is_visible()
                            page.locator('#shippingWorldMap.sw119c-land-ready').wait_for(timeout=15000)
                            page.locator('#shippingWorldMap.sw119c-borders-ready').wait_for(timeout=15000)
                            assert page.locator('#sw119cLandDetail').count()==1
                            assert page.locator('#sw119cBorderDetail').count()==1
                            assert page.locator('#shippingMapSvg image[href="brand/world-land-ne110.svg"]').count()==1
                            assert page.locator('#shippingMapCount').is_visible()
                            assert page.locator('.sw-atlas-legend').count()==1
                            assert not page.locator('.sw-atlas-legend').is_visible()
                            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3'),(width,theme,'page overflow')
                            # On mobile, form fields, rail and title should not cover each other.
                            coords=page.evaluate("""() => {
                              const r=q=>{const x=document.querySelector(q);const v=x.getBoundingClientRect();
                                return {x:v.x,y:v.y,w:v.width,h:v.height,bottom:v.bottom,right:v.right}};
                              return {title:r('#shippingWorldMap .sw-atlas-head'),
                                form:r('#shippingWorldMap .sw-atlas-controlbar'),
                                rail:r('#shippingWorldMap .sw-atlas-toolbar'),
                                presets:r('.sw119b-presets'),
                                zoom:r('.sw-atlas-zoom'),
                                count:r('#shippingMapCount')}
                            }""")
                            assert coords['title']['bottom'] <= coords['form']['y']+3,(width,theme,'title-overlaps-form',coords)
                            assert coords['form']['bottom'] <= coords['rail']['y']+3,(width,theme,'form-overlaps-rail',coords)
                            def overlapping(a,b):
                                return min(a['right'],b['right'])-max(a['x'],b['x'])>3 and min(a['bottom'],b['bottom'])-max(a['y'],b['y'])>3
                            assert not overlapping(coords['presets'],coords['zoom']),(width,theme,'preset-overlaps-zoom',coords)
                            assert not overlapping(coords['presets'],coords['count']),(width,theme,'preset-overlaps-count',coords)
                            assert not overlapping(coords['zoom'],coords['count']),(width,theme,'zoom-overlaps-count',coords)
                            # Open a source-backed port, focus it, verify pan/zoom camera stays synchronized.
                            page.locator('#shippingMapPick').select_option('NL-RTM')
                            assert page.locator('#shippingMapInspector').is_visible()
                            assert 'Rotterdam' in page.locator('#shippingMapDetailTitle').inner_text()
                            if width>=901:
                                page.locator('#sw119DetailActions .sw119-country-context').wait_for(timeout=10000)
                                assert 'country total' in page.locator('#sw119DetailActions .sw119-country-context').inner_text().lower()
                            initial=page.locator('#shippingMapSvg').get_attribute('viewBox')
                            page.locator('#sw119bFocusSelection').click()
                            focused=page.locator('#shippingMapSvg').get_attribute('viewBox')
                            assert focused!=initial
                            # On phone focus button closes bottom sheet so user actually sees map.
                            if width<=900: assert not page.locator('#shippingMapInspector').is_visible()
                            page.locator('[data-map-zoom="reset"]').click()
                            assert page.locator('#shippingMapSvg').get_attribute('viewBox')=='0 0 900 388'
                            page.locator('.sw119b-presets button[data-preset="north sea"]').click()
                            assert page.locator('#shippingMapSvg').get_attribute('viewBox')!='0 0 900 388'
                            page.locator('[data-map-zoom="in"]').click()
                            assert page.locator('#shippingMapSvg').get_attribute('viewBox')!='0 0 900 388'
                            page.locator('[data-map-zoom="reset"]').click()
                            assert page.locator('#shippingMapSvg').get_attribute('viewBox')=='0 0 900 388'
                            assert page.locator('#offshoreRates .sw-offshore-card').count()==4
                            assert page.locator('#usdaRateCards .sw-usda-card').count()==2
                            assert page.locator('#voyageEstimator').count()==1
                            assert page.locator('#navprofitEconomics').count()==1
                            assert not errors,(width,theme,errors)
                            if theme=='dark' and width in (390,1672):
                                page.locator('[data-map-zoom="reset"]').click()
                                page.evaluate("document.body.classList.add('sw119-inspector-hidden')")
                                page.evaluate('window.scrollTo(0,0)')
                                out=ROOT/'workspace-previews'/f'shipping-polish-v119b-{width}.png'
                                out.parent.mkdir(parents=True,exist_ok=True)
                                page.screenshot(path=str(out),animations='disabled',timeout=30000)
                            summary.append({'width':width,'theme':theme,'ports':40,
                                            'unobstructed':True,'synced_focus':True})
                        finally:
                            page.close()
                # High-detail file failures must not remove the original
                # 1:110m land silhouette or the 40 selectable port anchors.
                fallback=browser.new_page(viewport={'width':390,'height':860})
                fallback.route('**/brand/world-land-ne50-v119c.svg',lambda route:route.abort())
                fallback.route('**/brand/world-borders-ne50-v119c.svg',lambda route:route.abort())
                fallback.goto(f'http://127.0.0.1:{server.server_port}/shipping.html',wait_until='domcontentloaded')
                fallback.locator('#shippingMapPins .sw-atlas-point').first.wait_for(timeout=30000)
                assert fallback.locator('#shippingMapPins .sw-atlas-point').count()==40
                assert fallback.locator('#shippingMapSvg image[href="brand/world-land-ne110.svg"]').count()==1
                fallback.wait_for_timeout(300)
                assert not fallback.locator('#shippingWorldMap').evaluate("(e)=>e.classList.contains('sw119c-land-ready')")
                fallback.close()
            finally:browser.close()
    finally:server.shutdown();server.server_close()
    assert len(summary)==14
    print(json.dumps({'result':'PASS','checks':summary},indent=2))

if __name__=='__main__':run()
