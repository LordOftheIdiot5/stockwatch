import functools,http.server,pathlib,threading,json
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}"
    with sync_playwright() as p:
      b=p.chromium.launch(headless=True,args=["--no-sandbox"])
      try:
        for width in (1440,390):
          for theme in ("dark","light"):
            page=b.new_page(viewport={"width":width,"height":900})
            page.add_init_script(f"localStorage.setItem('stockwatch-theme','{theme}')")
            errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(base+"/index.html")
            page.locator("#workspaceCoverage").wait_for()
            assert "213" in page.locator(".sw-ws-cover-number").inner_text()
            assert page.locator(".sw-heat-cell").count()==213
            assert page.locator(".sw-heat-cell.no-data").count()>=75
            page.locator("#workspaceCoverage").select_option("observed")
            assert page.locator(".sw-heat-cell.no-data").count()==0
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
            page.goto(base+"/stocks.html")
            page.locator("#stockCount").wait_for()
            assert "213 of 213" in page.locator("#stockCount").inner_text()
            page.locator(".sw-advanced-filters summary").click()
            page.locator("#stkMove").fill("0")
            assert int(page.locator("#stockCount").inner_text().split()[0])<=138
            page.locator("#stkResetMetrics").click()
            assert "213 of 213" in page.locator("#stockCount").inner_text()
            page.locator(".sw-universe-switch a").nth(1).click()
            page.locator("#stockCount").wait_for()
            assert int(page.locator("#stockCount").inner_text().split()[0])>1000
            assert page.locator("#stocksRows tr").count()==50
            page.locator("#stkSearch").fill("BBG000C7VJK2")
            assert page.locator("#stocksRows tr").count()==1
            assert "Reference only" in page.locator("#stocksRows").inner_text()
            page.locator("#stocksRows a").first.click()
            page.wait_for_function("document.querySelector('#query').value==='BBG000C7VJK2'")
            assert not errors,errors
            page.close()
      finally:b.close();server.shutdown();server.server_close()
if __name__=="__main__":main()
