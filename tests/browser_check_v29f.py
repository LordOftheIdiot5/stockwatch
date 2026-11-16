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
          page=b.new_page(viewport={"width":width,"height":900})
          errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
          page.goto(base+"/spreads.html")
          page.locator("#abDiscovery").wait_for(timeout=20000)
          assert page.locator("#abDiscovery .sw-peer").count()==9
          assert page.locator("#spreadPairs button").count()==12
          assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
          page.goto(base+"/price-history.html")
          page.locator("#pricePriority").wait_for()
          assert page.locator("#pricePriority tbody tr").count()==17
          assert "Awaiting licensed prices" in page.locator("#pricePriority").inner_text()
          assert not errors,errors
          page.close()
        b.close()
 finally:server.shutdown();server.server_close()
if __name__=="__main__":main()
