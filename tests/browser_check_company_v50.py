"""Real company-page browser checks, including permitted history fixture in memory only."""
import functools,http.server,threading,json
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
            page.goto(base+"company.html?ticker=NOVO-B.CO")
            page.locator("[data-company-tab=financials]").click()
            page.locator(".sw50-statement").wait_for(state="visible")
            assert "Q3 2026" in page.locator(".sw50-filing").first.inner_text()
            assert "Reported operating margin" in page.locator(".sw50-ratios").inner_text()
            assert "Adjusted operating margin" in page.locator(".sw50-ratios").inner_text()
            assert "DKK" in page.locator(".sw50-statement").inner_text()
            assert page.locator("[data-company-section=events]").count()==1
            assert page.locator("#individualChart").count()==1
            page.locator("[data-company-tab=financials]").click()
            page.screenshot(path=str(out/f"v50-financials-{width}.png"))
            page.goto(base+"company.html?ticker=SALM.OL")
            page.locator(".sw50-coverage").wait_for()
            page.locator("[data-company-tab=financials]").click()
            assert "No verified numeric statements" in page.locator("[data-company-section=financials]").inner_text()
            assert "does not mean" in page.locator("[data-company-section=events]").inner_text()
            page.wait_for_function("!document.querySelector('#companyHistorySource').innerText.includes('Checking')")
            page.evaluate("scrollTo(0,0)")
            page.screenshot(path=str(out/f"v50-nohistory-{width}.png"))
            fixture={"ticker":"SALM.OL","currency":"NOK","adjusted":False,"source":"ISOLATED TEST FIXTURE","sourceUrl":"https://example.com/test","licenseReference":"https://example.com/test-license","redistributionPermitted":True,"bars":[{"date":f"2026-10-{i:02d}","close":100+i,"open":99+i,"high":101+i,"low":98+i,"volume":1000+i} for i in range(1,26)]}
            page.route("**/data/history/SALM.OL.json*",lambda route:route.fulfill(status=200,content_type="application/json",body=json.dumps(fixture)))
            page.reload()
            page.locator("#individualChart [data-candle]").first.wait_for()
            assert page.locator("#individualChart [data-candle]").count()==25
            assert "ISOLATED TEST FIXTURE" in page.locator("#companyHistorySource").inner_text()
            page.locator("#individualChart [data-act=rsi]").click()
            assert page.locator("#individualChart .sw49-rsi svg").is_visible()
            page.locator("#individualChart").scroll_into_view_if_needed()
            page.screenshot(path=str(out/f"v50-fixture-{width}.png"))
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2"),width
            assert not errors,errors
            page.close()
        browser.close()
finally:
    server.shutdown()
