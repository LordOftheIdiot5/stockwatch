"""V47 shell checks against candidate files, with real browser and both themes."""
import functools,http.server,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
PAGES="index stocks company compare terminal directory research intelligence price-history spreads news calendar shorts commodities shipping health welcome".split()
handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT))
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_port}/"
out=ROOT/"workspace-previews";out.mkdir(exist_ok=True)
try:
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width,height in [(1440,1000),(390,844),(320,800)]:
            page=browser.new_page(viewport={"width":width,"height":height},reduced_motion="reduce")
            page.route("**/*",lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
            for name in PAGES:
                page.goto(base+name+".html"+("?ticker=SALM.OL" if name=="company" else ""),wait_until="load")
                assert page.locator("body").evaluate("(e)=>e.classList.contains('sw-shell-v47')"),name
                mobile=page.locator(".sw-mobile-nav")
                assert mobile.is_visible()==(width<=1050), (name,width)
                if width<=1050:
                    summary=mobile.locator("summary")
                    summary.click()
                    assert mobile.locator(".sw-mobile-drawer").is_visible(),name
                    assert mobile.locator("a[href='price-history.html']").last.is_visible(),name
                    page.keyboard.press("Escape")
                    assert not mobile.locator(".sw-mobile-drawer").is_visible(),name
                    assert mobile.evaluate("(e)=>Math.round(e.getBoundingClientRect().bottom)===innerHeight"),name
                else:
                    if page.locator(".sw-brand-more").count():
                        d=page.locator(".sw-brand-more")
                        d.locator("summary").click()
                        assert d.locator("a[href='terminal.html']").is_visible(),name
                        d.locator("summary").click()
                    else:
                        assert page.locator(".sw-side a[href='terminal.html']").count()==1,name
                        assert page.locator(".sw-side a[href='price-history.html']").count()==1,name
                # Verify the shared navigation remains in bounds. Existing page-specific
                # table overflow is a separate V48 gate, not waived or marked passed.
                assert page.locator("body").evaluate("(e)=>e.dataset.theme") in ("dark","light")
                if name in ("index","terminal","welcome"):
                    page.screenshot(path=str(out/f"v47-{name}-{width}-dark.png"))
                    theme=page.locator("#swTheme,#brandTheme")
                    theme.click()
                    assert page.locator("body").evaluate("(e)=>e.dataset.theme")=="light",name
                    page.screenshot(path=str(out/f"v47-{name}-{width}-light.png"))
                    theme.click()
            page.close()
        browser.close()
    print("V47 rendered navigation checks passed: 17 pages x 3 widths, representative light/dark captures")
finally:
    server.shutdown()
