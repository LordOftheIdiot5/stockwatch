import functools,http.server,pathlib,threading
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}"
    out=ROOT/"workspace-previews";out.mkdir(exist_ok=True)
    try:
      with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
        for width in (1440,390):
          for theme in ("dark","light"):
            page=browser.new_page(viewport={"width":width,"height":900})
            page.add_init_script(f"localStorage.setItem('stockwatch-theme','{theme}')")
            errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(base+"/intelligence.html?ticker=FRO.OL")
            page.locator(".sw-intel-center strong").wait_for(timeout=20000)
            assert page.locator(".sw-intel-center strong").inner_text()=="Frontline"
            assert page.locator("#intelContextCards .sw-peer").count()==4
            page.locator("#intelContextCards").get_by_text("Published series",exact=False).first.wait_for()
            page.locator("#intelSearch").fill("Equinor")
            assert page.locator(".sw-intel-center strong").inner_text()=="Equinor"
            assert "REFERENCE ONLY" in page.locator(".sw-intel-center").inner_text()
            page.locator("#intelSearch").fill("no-matching-test")
            page.get_by_text("No matching listings.",exact=True).wait_for()
            page.locator("#intelSearch").fill("Frontline")
            page.locator(".sw-intel-center strong").wait_for()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
            page.screenshot(path=str(out/f"v26-graph-{width}-{theme}.png"),full_page=True)
            page.goto(base+"/company.html?ticker=FRO.OL")
            page.locator(".sw-intel-summary").wait_for()
            assert page.locator(".sw-intel-summary a[href='intelligence.html?ticker=FRO.OL']").count()==1
            assert not errors,errors
            page.close()
        browser.close()
    finally:server.shutdown();server.server_close()
if __name__=="__main__":main()
