import functools,http.server,json,pathlib,threading
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}"
    try:
      with sync_playwright() as p:
        b=p.chromium.launch(headless=True,args=["--no-sandbox"])
        for width in (1440,390):
          for theme in ("dark","light"):
            page=b.new_page(viewport={"width":width,"height":900})
            page.add_init_script(f"localStorage.setItem('stockwatch-theme','{theme}')")
            errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(base+"/price-history.html")
            page.get_by_text("No licensed reference price series have been imported.",exact=False).wait_for()
            id="ref:XOSL:EQNR"
            r={"listingId":id,"mic":"XOSL","priceType":"end_of_day","redistributionPermitted":True,"close":102,"changePct":2,"lastDate":"2025-01-03","previousDate":"2025-01-02","currency":"NOK","source":"Fixture only","sourceUrl":"https://example.invalid/source","licenseReference":"https://example.invalid/license","historyPath":"data/licensed-reference-history/"+"a"*32+".json","adjusted":False}
            page.route("**/data/licensed-price-coverage.json",lambda route:route.fulfill(json={"records":[r]}))
            page.route("**/data/licensed-reference-history/**",lambda route:route.fulfill(json={**r,"bars":[{"date":"2025-01-02","close":100},{"date":"2025-01-03","close":102}]}))
            page.goto(base+"/stocks.html?q=Equinor")
            page.get_by_text("Licensed EOD · 2025-01-03",exact=True).wait_for()
            page.get_by_role("link",name="Price history ↗").click()
            page.locator("#licensedSeries .sw-chart-pro").wait_for()
            assert "Fixture only" in page.locator("#licensedSeries").inner_text()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
            assert not errors,errors
            page.close()
        b.close()
    finally:server.shutdown();server.server_close()
if __name__=="__main__":main()
