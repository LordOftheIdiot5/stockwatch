"""V116f: truthful compact Overview and browser-zoom evidence.

Do not claim native 200% browser zoom if headless browser shortcuts cannot
change real browser zoom. A responsive-width+DPR2 gate remains a separate test.
"""
import functools
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
WIDTHS=(1440,1672,1920)
MAX_HEAT_TOP={1440:900,1672:900,1920:885}

def main():
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
        functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    rows=[]
    zoom={}
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                for width in WIDTHS:
                    for theme in ('dark','light'):
                        page=browser.new_page(viewport={'width':width,'height':941},
                            reduced_motion='reduce',device_scale_factor=1)
                        page.add_init_script('localStorage.setItem("stockwatch-theme",'+json.dumps(theme)+')')
                        errors=[]
                        page.on('pageerror',lambda e:errors.append(str(e)))
                        try:
                            page.goto(f'http://127.0.0.1:{server.server_port}/index.html',
                                wait_until='domcontentloaded',timeout=30000)
                            page.locator('.sw110e-world').wait_for(timeout=30000)
                            page.locator('.sw116c-overview-grid').wait_for(timeout=30000)
                            heat=page.locator('.sw-ws-heatmap').bounding_box()
                            chart=page.locator('.sw92-focus-chart').bounding_box()
                            svg=page.locator('#overviewMacroPlot svg').bounding_box()
                            coverage=page.locator('.sw110d-market-coverage')
                            assert heat and chart and svg
                            assert page.locator('.sw110e-map-heading').count()==0
                            assert 'NOT market returns' in coverage.inner_text()
                            assert '152 / 500' in coverage.inner_text() or 'research listings have a dated price observation' in coverage.inner_text()
                            details=page.locator('.sw110e-all-venues')
                            collapsed_coverage_height=coverage.bounding_box()['height']
                            assert collapsed_coverage_height<310,(width,theme,collapsed_coverage_height)
                            assert not details.evaluate('(e)=>e.open')
                            assert not coverage.locator('.sw110d-coverage-foot').is_visible()
                            details.locator('summary').focus()
                            page.keyboard.press('Enter')
                            assert details.evaluate('(e)=>e.open')
                            assert coverage.locator('.sw110d-coverage-foot').is_visible()
                            assert 'Venue bars show observation coverage' in coverage.inner_text()
                            assert 2.1<svg['width']/svg['height']<2.4
                            assert abs(svg['width']-chart['width'])<120
                            assert heat['y']<=MAX_HEAT_TOP[width],(width,theme,heat['y'])
                            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3')
                            assert not errors,errors
                            rows.append({'width':width,'theme':theme,
                                'heatTop':round(heat['y'],1),
                                'chartHeight':round(chart['height'],1),
                                'chartSvgHeight':round(svg['height'],1),
                                'collapsedCoverageHeight':round(collapsed_coverage_height,1),
                                'expandedCoverageHeight':round(coverage.bounding_box()['height'],1)})
                        finally:page.close()
                # Browser shortcut experiment: report a *measured* layout
                # viewport change, not an assumed native zoom success.
                page=browser.new_page(viewport={'width':1440,'height':900},
                    reduced_motion='reduce')
                try:
                    page.goto(f'http://127.0.0.1:{server.server_port}/index.html',
                        wait_until='domcontentloaded',timeout=30000)
                    before=page.evaluate('({width:innerWidth,dpr:devicePixelRatio})')
                    for _ in range(5):page.keyboard.press('Control+Equal')
                    page.wait_for_timeout(250)
                    after=page.evaluate('({width:innerWidth,dpr:devicePixelRatio,scroll:document.documentElement.scrollWidth})')
                    zoom={'method':'Chromium headless Ctrl+Equal keyboard experiment',
                          'before':before,'after':after,
                          'nativeZoomDetected':after['width']<before['width']-50}
                    if zoom['nativeZoomDetected']:
                        assert after['scroll']<=after['width']+3,zoom
                    # Otherwise this environment cannot certify browser-UI zoom.
                finally:page.close()
            finally:browser.close()
    finally:
        server.shutdown()
        server.server_close()
    assert len(rows)==len(WIDTHS)*2
    print(json.dumps({'v116f':'pass','desktop':rows,
        'browserZoomDiagnostic':zoom},indent=2))

if __name__=='__main__':main()
