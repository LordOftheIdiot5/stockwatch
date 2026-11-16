import functools,http.server,pathlib,threading
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
            page.goto(base+"/index.html")
            page.locator("#workspaceCoverage").wait_for(timeout=20000)
            assert "500" in page.locator(".sw-ws-cover-number").inner_text()
            assert page.locator('.sw-heat-cell.no-data').count()==0
            page.locator("#workspaceCoverage").select_option("all")
            assert page.locator('.sw-heat-cell').count()==500
            assert page.locator('.sw-heat-cell.no-data').count()>=362
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
            page.goto(base+"/stocks.html")
            page.locator("#stockCount").wait_for()
            assert "500 of 500" in page.locator("#stockCount").inner_text()
            page.locator('[data-screen="moves"]').click()
            assert page.locator("#stkMove").input_value()=="3"
            assert int(page.locator("#stockCount").inner_text().split()[0])<=138
            page.locator('[data-screen="all"]').click()
            assert "500 of 500" in page.locator("#stockCount").inner_text()
            page.locator("#stkSearch").fill("ASSA ABLOY")
            assert page.locator("#stocksRows").get_by_text("Reference only").count()>=1
            if page.locator("#swGlobalSearch").is_visible():
                page.locator("#swGlobalSearch").fill("Equinor")
                page.locator("#swQuickResults a").first.wait_for()
                assert "Equinor" in page.locator("#swQuickResults a").first.inner_text()
                page.locator("#swGlobalSearch").press("Escape")
                assert not page.locator("#swQuickResults").is_visible()
            assert not errors,errors
            page.close()
        b.close()
    finally:server.shutdown();server.server_close()
if __name__=="__main__":main()
