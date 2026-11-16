import functools,http.server,pathlib,threading
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            for width in (1440,390):
                page=browser.new_page(viewport={"width":width,"height":900})
                errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
                page.goto(base+"/stocks.html")
                page.get_by_text("213 of 213 research listings",exact=True).wait_for(timeout=20000)
                page.locator("#stkCoverage").select_option("reference")
                assert page.locator("#stockCount").inner_text()=="75 of 213 research listings"
                page.locator("#stkSearch").fill("Equinor")
                assert page.locator("#stockCount").inner_text()=="1 of 213 research listings"
                row=page.locator("#stocksRows tr")
                assert "Reference only" in row.inner_text()
                assert row.locator("a").get_attribute("href").startswith("research.html?instrument=")
                page.locator("#stkSearch").fill("")
                page.locator("#stkCoverage").select_option("monitored")
                assert page.locator("#stockCount").inner_text()=="138 of 213 research listings"
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
                assert not errors,errors
                page.close()
            browser.close()
    finally:server.shutdown();server.server_close()
if __name__=="__main__":main()
