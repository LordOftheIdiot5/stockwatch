"""N41 company-news desk and shared navigation browser acceptance."""
import functools
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def main():
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/"
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            try:
                for width in (320,390,1440):
                    for theme in ("dark","light"):
                        ctx=browser.new_context(viewport={"width":width,"height":900})
                        ctx.add_init_script("localStorage.setItem('stockwatch-theme',"+json.dumps(theme)+")")
                        page=ctx.new_page()
                        errors=[]
                        page.on("pageerror",lambda e:errors.append(str(e)))
                        page.route("**/*",lambda route:route.continue_() if route.request.url.startswith(base) else route.abort())
                        try:
                            page.goto(base+"unlisted.html",wait_until="load")
                            page.wait_for_function("document.querySelectorAll('.n41-news-row').length>=20")
                            page.locator("#n41-news-tier").select_option("reviewed")
                            assert page.locator(".n41-news-row").count()==20
                            assert "29 matching records" in page.locator("#n41-news-status").inner_text()
                            page.locator("#n41-news-more").click()
                            assert page.locator(".n41-news-row").count()==29
                            page.locator("#n41-news-company").select_option("reetec")
                            assert page.locator(".n41-news-row").count()==1
                            page.locator("#n41-news-company").select_option("rocsys")
                            assert page.locator(".n41-news-row").count()==1
                            page.locator("#n41-news-company").select_option("monumental")
                            assert page.locator(".n41-news-row").count()==2
                            page.locator("#n41-query").fill("Monumental")
                            assert page.locator(".n41-company:visible").count()==1
                            page.locator("#monumental").get_by_text("Read company news",exact=True).click()
                            assert page.locator("#n41-news-company").input_value()=="monumental"
                            assert page.locator(".n41-news-row").count()==2
                            page.locator("#n41-query").fill("")
                            page.locator("#n41-news-company").select_option("mistral")
                            assert page.locator(".n41-news-row").count()==2
                            page.locator("#n41-news-company").select_option("neura")
                            assert page.locator(".n41-news-row").count()==2
                            page.locator("#n41-news-category").select_option("Partnerships")
                            assert page.locator(".n41-news-row").count()==2
                            page.locator("#n41-news-category").select_option("")
                            page.locator("#n41-query").fill("Saga Robotics")
                            assert page.locator(".n41-company:visible").count()==1
                            page.locator("#saga").get_by_text("Read company news",exact=True).click()
                            assert page.locator("#n41-news-company").input_value()=="saga"
                            assert page.locator(".n41-news-row").count()==1
                            assert page.locator("body").get_attribute("data-theme")==theme
                            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2"),(width,theme)
                            assert page.locator(".sw-mobile-drawer a[href='unlisted.html']").count()==1
                            assert page.locator(".sw-brand-drawer a[href='unlisted.html']").count()==1
                            assert not errors,errors
                            page.goto(base+"stocks.html",wait_until="load")
                            page.locator("#n41-listed-expansion summary").click()
                            assert page.locator(".n41-listed-candidate:visible").count()==7
                            page.locator("#n41-resource-chain summary").click()
                            assert page.locator(".n41-resource-group:visible").count()==4
                            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2"),(width,theme)
                            assert not errors,errors
                            page.goto(base+"unlisted.html",wait_until="load")
                            page.locator(".n41-news-row").first.wait_for(state="visible")
                            out=ROOT/"workspace-previews";out.mkdir(exist_ok=True)
                            page.screenshot(path=str(out/f"n41-news-{width}-{theme}.png"),animations="disabled")
                            print("PASS N41",width,theme)
                        finally:
                            ctx.close()
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()

if __name__=="__main__":main()
