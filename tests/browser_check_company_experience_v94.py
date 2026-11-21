"""V94 company design interactive browser and screenshot QA.

Uses existing public fixture pages; never synthesizes or publishes price
history. The independent V50 company browser test validates in-memory history.
"""
import functools
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
SIZES={"mobile":390,"tablet":768,"desktop":1440,"wide":1920}
TICKERS=("NOVO-B.CO","SALM.OL")
def main():
    out=ROOT/"visual-audit"/"v94-company"
    out.mkdir(parents=True,exist_ok=True)
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),
        functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    captures=[]
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True,args=["--no-sandbox"])
            for ticker in TICKERS:
                for viewport,width in SIZES.items():
                    for theme in ("dark","light"):
                        page=browser.new_page(viewport={"width":width,"height":900},
                                              reduced_motion="reduce")
                        errors=[]
                        page.on("pageerror",lambda e:errors.append(str(e)))
                        page.add_init_script(
                            f"localStorage.setItem('stockwatch-theme','{theme}')")
                        try:
                            response=page.goto(
                                f"http://127.0.0.1:{server.server_port}/company.html?ticker={ticker}",
                                wait_until="domcontentloaded",timeout=25000)
                            profile=page.locator("#stockDetail .sw-company-research")
                            profile.wait_for(timeout=30000)
                            page.locator(".sw94-research-shortcuts").wait_for(timeout=10000)
                            chart=profile.locator('[data-company-section="chart"]')
                            map_node=profile.locator("#companyDriverMap")
                            assert chart.count()==1
                            assert map_node.count()==1
                            assert chart.evaluate(
                                "(el)=>el.nextElementSibling?.id==='companyDriverMap'")
                            tabs=profile.locator("[data-company-tab]")
                            assert tabs.count()==7
                            assert tabs.first.get_attribute("aria-current")=="location"
                            assert profile.locator("#companyHistorySource").get_attribute("aria-live")=="polite"
                            assert profile.locator("#individualChart").get_attribute("role")=="region"
                            tabs.nth(1).focus()
                            tabs.nth(1).press("ArrowRight")
                            assert tabs.nth(2).evaluate("(el)=>el===document.activeElement")
                            tabs.nth(1).click()
                            assert tabs.nth(1).get_attribute("aria-current")=="location"
                            assert tabs.nth(1).get_attribute("aria-controls")=="sw94-company-financials"
                            assert not errors,errors
                            assert page.evaluate(
                                "document.documentElement.scrollWidth<=innerWidth+2")
                            # Restore top fold for screenshot comparison.
                            page.evaluate("window.scrollTo(0,0)")
                            page.screenshot(path=str(
                                out/f"{ticker.replace('.','-')}-{viewport}-{theme}.png"),
                                animations="disabled",full_page=False)
                            captures.append({"ticker":ticker,"viewport":viewport,
                                "width":width,"theme":theme,
                                "status":response.status if response else None,
                                "errors":errors,"title":page.title()})
                        finally:
                            page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        (out/"audit.json").write_text(json.dumps(captures,indent=2),encoding="utf-8")
    print(json.dumps({"captures":len(captures),"errors":0,"output":str(out)}))
if __name__=="__main__":
    main()
