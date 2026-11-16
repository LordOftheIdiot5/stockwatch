import functools,http.server,pathlib,threading,json
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as p:
            b=p.chromium.launch(headless=True,args=["--no-sandbox"])
            for w in (1440,390):
                for theme in ("dark","light"):
                    page=b.new_page(viewport={"width":w,"height":900})
                    page.add_init_script(f"localStorage.setItem('stockwatch-theme',{json.dumps(theme)})")
                    errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
                    page.goto(base+"/research.html")
                    page.get_by_text("75 of 75 research listings",exact=False).wait_for()
                    assert page.locator("#historyMetrics .tile").count()==6
                    assert page.locator("#targetRows tr").count()==25
                    page.locator("#targetNext").click()
                    assert page.locator("#targetPage").inner_text()=="Page 2 of 3"
                    page.locator("#targetQuery").fill("Equinor")
                    page.locator("#targetRows a").first.click()
                    page.get_by_text("Observed mapping history",exact=True).wait_for()
                    assert page.locator("#targetDetail").get_by_text("Share-class FIGI",exact=True).count()==1
                    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
                    assert not errors,errors
                    page.close()
            b.close()
    finally:server.shutdown();server.server_close()
if __name__=="__main__":main()
