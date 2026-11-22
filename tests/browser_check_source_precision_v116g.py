"""V116g source-truth regression.

A conservative provider-date comparison must never be advertised as an
exchange-certified close or inferred licence. Exercise keyboard disclosure
and both themes at native CSS viewport widths.
"""
import functools
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
TARGETS=(390,720,1440,1672)

def main():
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
        functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    checks=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                for width in TARGETS:
                    for theme in ('dark','light'):
                        page=browser.new_page(viewport={'width':width,'height':941},
                            reduced_motion='reduce')
                        page.add_init_script('localStorage.setItem("stockwatch-theme",'+json.dumps(theme)+')')
                        errors=[]
                        page.on('pageerror',lambda e:errors.append(str(e)))
                        try:
                            response=page.goto(f'http://127.0.0.1:{server.server_port}/index.html',
                                wait_until='domcontentloaded',timeout=30000)
                            source=page.locator('details.sw96-source-status')
                            source.wait_for(timeout=30000)
                            summary=source.locator('summary')
                            summary_text=summary.inner_text()
                            assert 'Source freshness' in summary_text,(width,summary_text)
                            assert 'session-verified' not in summary_text,(width,summary_text)
                            assert ('date-comparable' in summary_text or
                                'Date coverage unavailable' in summary_text),(width,summary_text)
                            assert not source.evaluate('(e)=>e.open')
                            summary.focus()
                            page.keyboard.press('Enter')
                            assert source.evaluate('(e)=>e.open'),(width,theme,'keyboard disclosure')
                            detail=source.locator('.sw96-source-detail').inner_text()
                            assert 'UTC weekday cutoff' in detail,detail
                            assert 'not venue-certified daily closes' in detail,detail
                            assert 'redistribution licence' in detail,detail
                            assert 'Older moves are not live alerts' in detail,detail
                            assert source.locator('a[href="health.html"]').is_visible()
                            summary.focus()
                            page.keyboard.press('Enter')
                            assert not source.evaluate('(e)=>e.open')
                            assert response and response.status==200
                            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3'),(width,theme)
                            assert not errors,errors
                            checks.append({'width':width,'theme':theme,
                                'summary':summary_text[:120],
                                'keyboardDisclosure':True,
                                'noOfficialCloseClaim':True})
                        finally:page.close()
            finally:browser.close()
    finally:
        server.shutdown()
        server.server_close()
    assert len(checks)==len(TARGETS)*2
    print(json.dumps({'v116g':'passed','cases':checks,
        'note':'CSS responsive test, not native 200% browser zoom'},indent=2))

if __name__=='__main__':
    main()
