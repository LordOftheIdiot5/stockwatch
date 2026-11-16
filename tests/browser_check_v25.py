"""V25 browser checks: fixture-only price observations, never published as market data."""
import functools,http.server,json,pathlib,threading
from urllib.parse import quote
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}"
    ticker=json.loads((ROOT/"watchlist.json").read_text())["tickers"][0]["ticker"]
    url=base+"/company.html?ticker="+quote(ticker)
    fixture={"ticker":ticker,"source":"Browser test fixture","sourceUrl":"https://example.org/source","licenseReference":"https://example.org/test","currency":"NOK","adjusted":False,"redistributionPermitted":True,"bars":[{"date":"2026-01-01","close":100},{"date":"2026-01-02","close":101},{"date":"2026-01-20","close":95}]}
    out=ROOT/"workspace-previews";out.mkdir(exist_ok=True)
    try:
      with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        for width in (1440,390):
          for theme in ("dark","light"):
            page=browser.new_page(viewport={"width":width,"height":900})
            page.add_init_script(f"localStorage.setItem('stockwatch-theme',{json.dumps(theme)})")
            errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.route("**/data/history/**",lambda route:route.fulfill(json=fixture))
            page.goto(url)
            chart=page.locator("#individualChart .sw-chart-pro")
            chart.wait_for(timeout=20000)
            assert chart.locator("output").inner_text()=="2026-01-20 · 95 NOK"
            chart.locator("input[type=range]").fill("1")
            assert chart.locator("output").inner_text()=="2026-01-02 · 101 NOK"
            assert "Browser test fixture" in page.locator("#companyHistorySource").inner_text()
            assert page.locator('.sw-identity-panel a[href="research.html"]').count()==1
            page.locator("[data-period='0']").click()
            assert "3 observations" in chart.inner_text()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
            page.unroute("**/data/history/**")
            page.route("**/data/history/**",lambda route:route.fulfill(json={**fixture,"redistributionPermitted":False}))
            page.reload()
            page.get_by_text("Licensed historical series not connected",exact=True).wait_for()
            assert page.locator("#individualChart .sw-chart-pro").count()==0
            page.screenshot(path=str(out/f"v25-no-licensed-history-{width}-{theme}.png"),full_page=True)
            assert not errors,errors
            page.close()
        browser.close()
    finally:server.shutdown();server.server_close()
if __name__=="__main__":main()
