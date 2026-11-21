"""V93 real-browser heatmap inspector test, separate from static QA."""
import functools
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
SIZES={"mobile":390,"desktop":1440}
def main():
    out=ROOT/"visual-audit"/"v93-heatmap"
    out.mkdir(parents=True,exist_ok=True)
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),
        functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    results=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            for name in ("index","stocks"):
                for device,width in SIZES.items():
                    for theme in ("dark","light"):
                        page=browser.new_page(viewport={"width":width,"height":900})
                        errors=[]
                        page.on("pageerror",lambda error:errors.append(str(error)))
                        page.add_init_script(f"localStorage.setItem('stockwatch-theme','{theme}')")
                        try:
                            response=page.goto(
                                f"http://127.0.0.1:{server.server_port}/{name}.html",
                                wait_until="domcontentloaded",timeout=25000)
                            if name=="stocks":
                                page.locator('[data-stk-view="heat"]').click(timeout=25000)
                            root=page.locator("#workspaceHeatmap" if name=="index" else "#stkHeat")
                            tiles=root.locator("a.sw-heat-cell")
                            tiles.first.wait_for(timeout=25000)
                            dock=page.locator(".sw93-heat-inspector")
                            dock.wait_for(timeout=10000)
                            count=tiles.count()
                            assert count>0
                            assert dock.locator(".sw93-heat-total").inner_text()==f"{count} visible tiles"
                            assert dock.locator(".sw93-heat-count").count()==4
                            tiles.first.focus()
                            assert dock.locator(".sw93-heat-detail-head").count()==1
                            assert dock.locator(".sw93-heat-link").count()==1
                            assert dock.locator(".sw93-heat-detail").get_attribute("aria-live")=="polite"
                            picker=dock.locator(".sw93-heat-picker")
                            assert picker.locator("option").count()==count+1
                            picker.select_option("0")
                            assert dock.locator(".sw93-heat-detail-head").count()==1
                            assert dock.locator(".sw93-heat-ticker").inner_text()==tiles.nth(0).locator("strong").inner_text()
                            # Focus on another tile: dropdown and detail must stay in sync.
                            if count>=2:
                                tiles.nth(1).focus()
                                assert picker.input_value()=="1"
                                assert dock.locator(".sw93-heat-ticker").inner_text()==tiles.nth(1).locator("strong").inner_text()
                            toggle=dock.locator(".sw93-heat-size")
                            toggle.click()
                            assert toggle.get_attribute("aria-pressed")=="true"
                            assert root.evaluate("(el)=>el.classList.contains('sw93-heat-comfortable')")
                            toggle.click()
                            assert toggle.get_attribute("aria-pressed")=="false"
                            if name=="stocks":
                                page.locator('[data-stk-view="table"]').click()
                                assert dock.is_hidden()
                                page.locator('[data-stk-view="heat"]').click()
                                dock.wait_for(state="visible",timeout=10000)
                            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
                            assert not errors,errors
                            page.screenshot(path=str(out/f"{name}-{device}-{theme}.png"),
                                            animations="disabled",full_page=False)
                            results.append({"page":name,"device":device,"theme":theme,
                                            "status":response.status if response else None,
                                            "tiles":count,"errors":errors})
                        finally:
                            page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        (out/"audit.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
    print(json.dumps({"captures":len(results),"errors":0,"output":str(out)}))
if __name__=="__main__":
    main()
