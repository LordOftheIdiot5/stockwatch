"""Browser smoke test for dedicated company research in both themes."""
import functools,http.server,json,pathlib,threading
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}"
    out=ROOT/"workspace-previews";out.mkdir(exist_ok=True)
    first=json.loads((ROOT/"watchlist.json").read_text())["tickers"][0]
    from urllib.parse import quote
    try:
      with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        for width in (1440,390):
          for theme in ("dark","light"):
            page=browser.new_page(viewport={"width":width,"height":900})
            page.add_init_script(f"localStorage.setItem('stockwatch-theme',{json.dumps(theme)})")
            errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(base+"/company.html?ticker="+quote(first["ticker"]))
            page.locator(".sw-company-heading h2").wait_for(timeout=20000)
            assert page.locator(".sw-company-heading h2").inner_text()
            assert page.locator("[data-company-section]").count()==5
            assert page.locator(".sw-identity-panel").count()==1
            assert page.locator("body").get_attribute("data-theme")==theme
            page.locator("[data-company-tab='peers']").click()
            assert page.locator(".sw-company-peers").is_visible()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
            page.screenshot(path=str(out/f"company-{width}-{theme}.png"),full_page=True)
            page.goto(base+"/stocks.html")
            page.locator(".sw-onboarding").wait_for()
            page.locator(".sw-onboarding summary").click()
            assert page.locator(".sw-onboard-grid>div").count()==17
            page.goto(base+"/company.html?ticker=NOT_A_REAL_TRACKED_TICKER")
            page.get_by_text("No tracked listing matches this identifier.",exact=False).wait_for()
            assert not errors,errors
            page.close()
        browser.close()
    finally:
      server.shutdown();server.server_close()
if __name__=="__main__":main()
