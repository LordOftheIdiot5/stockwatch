"""V22 browser check using actual generated reference data."""
import functools,http.server,json,pathlib,threading
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
                    page.add_init_script(f"localStorage.setItem('stockwatch-theme',{json.dumps(theme)})")
                    errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
                    page.goto(base+"/welcome.html")
                    assert page.locator(".brand img").evaluate("(img)=>img.complete && img.naturalWidth>0")
                    assert page.locator("body").get_attribute("data-theme")==theme
                    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
                    assert page.locator(".tile").count()==6
                    page.screenshot(path=str(out/f"welcome-{width}-{theme}.png"),full_page=True)
                    page.goto(base+"/directory.html")
                    page.wait_for_function("document.querySelector('#records').textContent !== '—'")
                    count=int(page.locator("#records").inner_text())
                    assert count>=100,count
                    assert page.locator("#directoryRows tr").count()==50
                    page.locator("#next").click()
                    assert page.locator("#pageCount").inner_text().startswith("Page 2 ")
                    page.locator("#query").fill("nonexistent-instrument-test-12345")
                    assert page.locator("#matches").inner_text()=="0"
                    page.locator("#query").fill("")
                    assert page.locator("#pageCount").inner_text().startswith("Page 1 ")
                    page.locator("#venue").select_option(index=1)
                    assert int(page.locator("#matches").inner_text())<=count
                    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
                    assert not errors,errors
                    page.screenshot(path=str(out/f"directory-{width}-{theme}.png"),full_page=True)
                    page.close()
            browser.close()
    finally:
        server.shutdown();server.server_close()
if __name__=="__main__":main()
