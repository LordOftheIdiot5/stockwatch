"""Rendered company network and photography checks at desktop and mobile widths."""
import functools,http.server,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_port}/"
out=ROOT/"workspace-previews";out.mkdir(exist_ok=True)
try:
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width,height in [(1440,1000),(390,844)]:
            page=browser.new_page(viewport={"width":width,"height":height},reduced_motion="reduce")
            page.route("**/*",lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
            errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(base+"intelligence.html?entity=spacex")
            host=page.locator("#commercialNetwork")
            host.locator(".sw-network-center").wait_for()
            assert "Space Exploration Technologies" in host.locator(".sw-network-center").inner_text()
            assert host.locator(".sw-network-evidence").count()==2
            host.locator("[data-network-hops]").select_option("2")
            assert host.locator(".sw-network-evidence").count()==3
            host.locator("[data-network-kind]").select_option("financing")
            assert host.locator(".sw-network-evidence").count()==1
            host.locator("[data-network-kind]").select_option("all")
            host.locator("[data-network-entity=singulus]").first.click()
            assert "SINGULUS" in host.locator(".sw-network-center").inner_text()
            page.screenshot(path=str(out/f"v84-network-{width}.png"))
            assert page.locator("#usResearch a.sw-peer").count()==50
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
            for ticker in ("XNAS:NVDA","XNAS:AAPL","WAWI.OL","HAUTO.OL"):
                page.goto(base+"company.html?ticker="+ticker)
                img=page.locator(".sw-company-photo img").first
                img.wait_for()
                img.scroll_into_view_if_needed()
                page.wait_for_function("document.querySelector('.sw-company-photo img').naturalWidth>0")
                assert page.locator(".sw-company-photo figcaption").first.inner_text().find("Original photograph")>=0
                if ticker.startswith("XNAS:"):
                    assert "Not connected" in page.locator(".sw-company-last").first.inner_text()
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
                page.screenshot(path=str(out/f"v84-{ticker.replace(':','-')}-{width}.png"))
            assert not errors,errors
            page.close()
        browser.close()
finally:
    server.shutdown()
