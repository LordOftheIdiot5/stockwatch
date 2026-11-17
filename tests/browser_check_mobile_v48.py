"""Exercise V48 pagination using real candidate HTML and repository data."""
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
        for width,height in [(1440,1000),(768,1024),(390,844),(320,800)]:
            page=browser.new_page(viewport={"width":width,"height":height},reduced_motion="reduce")
            page.route("**/*",lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
            errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(base+"news.html",wait_until="load")
            page.locator("#newsGroups .news-item").first.wait_for()
            assert page.locator("#newsGroups .news-item").count()<=12
            assert page.locator("#d1Ticker").evaluate("(e)=>e.getBoundingClientRect().top") < page.locator("#newsGroups").evaluate("(e)=>e.getBoundingClientRect().top")
            page.locator("#relevance").select_option("all")
            nxt=page.locator('#newsGroups [data-step="1"]')
            if nxt.count() and nxt.is_enabled():
                before=page.locator("#newsGroups .news-item-title").first.inner_text()
                nxt.click()
                assert page.locator("#newsGroups .news-item").count()<=12
                assert page.locator("#newsGroups .news-item-title").first.inner_text()!=before
                page.locator('#newsGroups [data-step="-1"]').click()
                assert page.locator("#newsGroups .news-item-title").first.inner_text()==before
            page.locator("#q").fill("zzzz-no-company-zzzz")
            assert page.locator("#newsGroups .news-item").count()==0
            page.locator("#q").fill("")
            page.screenshot(path=str(out/f"v48-news-{width}.png"))
            print("news",width,"height",page.locator("body").evaluate("(e)=>e.scrollHeight"))
            page.goto(base+"shipping.html",wait_until="load")
            page.locator("#routeGrid .sw-route").first.wait_for()
            assert page.locator("#routeGrid .sw-route").count()<=6
            first=page.locator("#routeGrid .sw-route-id").first.inner_text()
            page.locator("#routeGrid [data-compare]").first.click()
            nxt=page.locator('#routePager [data-route-page="1"]')
            if nxt.is_enabled():
                nxt.click()
                assert page.locator("#routeGrid .sw-route-id").first.inner_text()!=first
                assert first in page.locator("#routeCompareBody").inner_text()
                page.locator('#routePager [data-route-page="-1"]').click()
                assert page.locator("#routeGrid .sw-route-id").first.inner_text()==first
                assert page.locator("#routeGrid [data-compare]").first.get_attribute("aria-pressed")=="true"
            page.locator("#routeSearch").fill("zzzz-no-route-zzzz")
            assert page.locator("#routeGrid .sw-route").count()==0
            page.locator("#routeSearch").fill("")
            page.screenshot(path=str(out/f"v48-shipping-{width}.png"))
            print("shipping",width,"height",page.locator("body").evaluate("(e)=>e.scrollHeight"))
            for route in ("stocks.html","calendar.html","directory.html"):
                page.goto(base+route,wait_until="load")
                page.locator("table th").first.wait_for()
                assert page.locator("table th").first.evaluate("(e)=>getComputedStyle(e).position")=="sticky",route
            assert not errors,errors
            page.close()
        browser.close()
    print("V48 real browser pagination and sticky header checks passed")
finally:
    server.shutdown()
