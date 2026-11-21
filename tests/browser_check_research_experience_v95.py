"""V95 multi-page design and interaction evidence (live local files, no mock prices).

24 captures: directory, research, intelligence × 320/390/1440/1920 × dark/light.
"""
import functools
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PAGES=("directory","research","intelligence")
VIEWPORTS={"small-mobile":320,"mobile":390,"desktop":1440,"wide":1920}

def main():
    out=ROOT/"visual-audit"/"v95-research"
    out.mkdir(parents=True,exist_ok=True)
    server=http.server.ThreadingHTTPServer(
        ("127.0.0.1",0),
        functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    checks=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            for name in PAGES:
                for device,width in VIEWPORTS.items():
                    for theme in ("dark","light"):
                        page=browser.new_page(viewport={"width":width,"height":900},
                                              reduced_motion="reduce")
                        errors=[]
                        page.on("pageerror",lambda error:errors.append(str(error)))
                        page.add_init_script(
                            f"localStorage.setItem('stockwatch-theme','{theme}')")
                        try:
                            response=page.goto(
                                f"http://127.0.0.1:{server.server_port}/{name}.html",
                                wait_until="domcontentloaded",timeout=30000)
                            assert response is not None and response.status==200
                            assert page.locator("main#main-content").count()==1
                            assert page.locator(".sw95-skip").count()==1
                            assert page.evaluate("""() => [...document.styleSheets].some(
                                s => s.href?.includes('reference-design-v95.css'))""")
                            if name=="directory":
                                page.wait_for_function("""() =>
                                  !document.querySelector('#directoryStatus')?.textContent?.includes('Loading')
                                """,timeout=25000)
                                assert page.locator("#directoryRows tr").count()>=1
                                assert "not connected" in page.locator("main .lede").inner_text().lower()
                                page.locator("#query").fill("unfindable-v95-company-zzzz")
                                assert "No matching reference records" in page.locator("#directoryRows").inner_text()
                                page.locator("#query").fill("")
                                page.locator("#directoryRows tr").first.wait_for()
                            elif name=="research":
                                page.wait_for_function("""() =>
                                  !document.querySelector('#historyStatus')?.textContent?.includes('Loading')
                                """,timeout=25000)
                                page.locator(".sw95-hero-links a[href='#universe']").click()
                                assert page.evaluate("location.hash==='#universe'")
                                assert "not necessarily" not in page.locator("main").inner_text()[:70].lower()
                                page.evaluate("window.scrollTo(0,0)")
                            else:
                                page.locator(".sw95-graph-guide").wait_for(timeout=30000)
                                assert page.locator(".sw95-graph-kind").count()==3
                                page.locator(".sw95-intel-jump a[href='#intelMap']").click()
                                assert page.evaluate("location.hash==='#intelMap'")
                                assert "do not prove" in page.locator(".sw95-graph-disclaimer").inner_text()
                                page.locator(".sw-intel-center").wait_for(timeout=25000)
                                select=page.locator("#intelListing")
                                assert select.locator("option").count()>=1
                                assert page.locator("#sw95GraphSelection").get_attribute("aria-live")=="polite"
                                if select.locator("option").count()>1:
                                    select.select_option(index=1)
                                    assert "Selected instrument" in page.locator("#sw95GraphSelection").inner_text()
                            assert page.evaluate(
                              "document.documentElement.scrollWidth <= window.innerWidth + 2"
                            ),(name,device,theme)
                            assert not errors,errors
                            page.evaluate("window.scrollTo(0,0)")
                            page.screenshot(
                                path=str(out/f"{name}-{device}-{theme}.png"),
                                animations="disabled",full_page=False)
                            checks.append({"page":name,"device":device,"width":width,
                                           "theme":theme,"status":response.status,
                                           "documentWidth":page.evaluate(
                                             "document.documentElement.scrollWidth"),
                                           "errors":errors})
                        finally:
                            page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        (out/"audit.json").write_text(json.dumps(checks,indent=2),encoding="utf-8")
    print(json.dumps({"captures":len(checks),"errors":0,"output":str(out)}))

if __name__=="__main__":
    main()
