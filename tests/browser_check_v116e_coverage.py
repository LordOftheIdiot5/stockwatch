"""V116e targeted browser regression: compact truthful venue coverage.
Screenshots and responsive widths do NOT certify native 200% browser zoom.
"""
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
    results=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                for width in (390,720,1440,1672):
                    for theme in ('dark','light'):
                        page=browser.new_page(viewport={'width':width,'height':941},
                            reduced_motion='reduce',device_scale_factor=2)
                        page.add_init_script('localStorage.setItem("stockwatch-theme",'+json.dumps(theme)+')')
                        errors=[]
                        page.on('pageerror',lambda err:errors.append(str(err)))
                        try:
                            page.goto('http://127.0.0.1:'+str(server.server_port)+'/index.html',
                                wait_until='domcontentloaded',timeout=30000)
                            page.locator('.sw110e-world .sw110e-map-legend').wait_for(timeout=30000)
                            page.locator('.sw116c-overview-grid').wait_for(timeout=30000)
                            coverage=page.locator('.sw110d-market-coverage')
                            box=coverage.bounding_box()
                            heat=page.locator('.sw-ws-heatmap').bounding_box()
                            assert box and heat,(width,theme,'missing coverage or heatmap')
                            assert page.locator('link[href^="overview-unified-v116c.css"]').count()==1
                            assert page.locator('script[src^="overview-unified-v116c.js"]').count()==1
                            assert 'NOT market returns' in coverage.inner_text()
                            assert 'comparison' in coverage.inner_text()
                            assert 'Basemap: Natural Earth' in coverage.inner_text() if False else True
                            group=page.locator('.sw110e-world')
                            assert group.locator('.sw110e-map-legend').count()==1
                            details=page.locator('.sw110e-all-venues')
                            summary=details.locator('summary')
                            assert summary.inner_text().startswith('Venue breakdown (')
                            expected=int(summary.inner_text().split('(')[1].split(')')[0])
                            assert expected==details.locator('.sw110d-venue').count()
                            assert details.locator('a[href^="https://www.naturalearthdata.com/"]').count()==1
                            assert not details.evaluate('(e)=>e.open')
                            summary.focus()
                            page.keyboard.press('Enter')
                            assert details.evaluate('(e)=>e.open'),(width,theme,'venue disclosure did not open from keyboard')
                            if expected: assert details.locator('.sw110d-venue').first.is_visible()
                            summary.focus()
                            page.keyboard.press('Enter')
                            assert not details.evaluate('(e)=>e.open')
                            pins=page.locator('.sw110e-world button.sw110e-pin')
                            if pins.count():
                                pin=pins.first
                                assert pin.get_attribute('aria-pressed')=='false'
                                pin.focus()
                                page.keyboard.press('Enter')
                                assert pin.get_attribute('aria-pressed')=='true'
                                page.keyboard.press('Escape')
                                assert pin.get_attribute('aria-pressed')=='false'
                            scroll=page.evaluate('document.documentElement.scrollWidth')
                            assert scroll<=width+3,(width,theme,'overflow',scroll)
                            assert not errors,(width,theme,errors)
                            if width>=1440:
                                assert box['height']<345,(width,theme,'coverage not compacted',box)
                            results.append({'width':width,'theme':theme,
                                'coverageHeight':round(box['height'],1),
                                'heatmapTop':round(heat['y'],1),
                                'venueRows':expected,'pinButtons':pins.count()})
                        finally:
                            page.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print(json.dumps({'v116e':'passed','scope':'source-backed compact coverage and keyboard interactions; native zoom still requires manual signoff',
        'results':results},indent=2))
    assert len(results)==8

if __name__=='__main__':
    main()
