"""V116b: check responsive layout at CSS widths comparable to 200% desktop zoom.

At 200% native browser zoom, a 1440/1672/1920 physical pixel window has
roughly 720/836/960 CSS pixels available. These tests exercise that resulting
responsive layout with DPR=2. This is NOT a certification of native zoom:
actual browser UI zoom and assistive technology still need owner QA.
"""
import functools
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
TARGETS={
 "Overview":"index.html",
 "Company":"company.html?ticker=NHY.OL",
 "News":"news.html",
 "Data products":"data-products.html",
 "Research terminal":"terminal.html",
}
WIDTHS=(720,836,960)

def main():
    server=http.server.ThreadingHTTPServer(
        ('127.0.0.1',0),
        functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    out=ROOT/'workspace-previews'
    out.mkdir(parents=True,exist_ok=True)
    metrics=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                for width in WIDTHS:
                    for theme in ('dark','light'):
                        context=browser.new_context(
                            viewport={'width':width,'height':900},
                            device_scale_factor=2,reduced_motion='reduce')
                        context.add_init_script(
                            'localStorage.setItem("stockwatch-theme",'+json.dumps(theme)+')')
                        try:
                            for name,path in TARGETS.items():
                                page=context.new_page()
                                errors=[]
                                page.on('pageerror',lambda error:errors.append(str(error)))
                                try:
                                    res=page.goto(
                                        f'http://127.0.0.1:{server.server_port}/'+path,
                                        wait_until='domcontentloaded',timeout=30000)
                                    page.locator('main').wait_for(timeout=15000)
                                    if name=='Overview':
                                        page.locator('#overviewMacroPlot svg').wait_for(timeout=30000)
                                        page.locator('.sw98-market-secondary .sw-ws-heatmap').wait_for(timeout=30000)
                                        assert 'not a stock index' in page.locator(
                                            '.sw98-primary .sw92-focus-chart').inner_text()
                                    page.wait_for_timeout(80)
                                    measure=page.evaluate("""() => ({
                                        scroll:document.documentElement.scrollWidth,
                                        viewport:innerWidth,
                                        body:document.body.scrollWidth,
                                        dpr:devicePixelRatio,
                                        heading:document.querySelector('main h1')?.innerText||'',
                                        clipping:[...document.querySelectorAll('main a,main button,main select')]
                                            .filter(x=>{const r=x.getBoundingClientRect();
                                                return r.width>0 && r.right>innerWidth+3}).length
                                    })""")
                                    assert res and res.status==200,(name,width,'HTTP')
                                    assert measure['heading'],(name,width,'missing main heading')
                                    assert measure['scroll']<=width+3,(name,width,measure)
                                    assert not errors,(name,width,errors[:5])
                                    if name=='Overview' and theme=='dark':
                                        page.screenshot(
                                            path=str(out/f'v116b-overview-equivalent-zoom-{width}.png'),
                                            animations='disabled')
                                    metrics.append({'page':name,'cssWidth':width,'theme':theme,
                                      'physicalWindowEquivalentPx':width*2,
                                      'scrollWidth':measure['scroll']})
                                finally:
                                    page.close()
                        finally:
                            context.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print(json.dumps({'v116b':'pass',
      'scope':'responsive CSS-width equivalent of 200% desktop zoom, not native zoom',
      'tested':len(metrics),'cases':metrics},indent=2))
    assert len(metrics)==len(TARGETS)*len(WIDTHS)*2

if __name__=='__main__':
    main()
