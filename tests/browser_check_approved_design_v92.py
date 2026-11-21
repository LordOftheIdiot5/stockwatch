"""V92 real-browser design checkpoint; screenshots and geometry, not a mock-data generator."""
import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
PAGES=("index","stocks","terminal","news","shipping","commodities",
       "spreads","compare","calendar","shorts","health")
WIDTHS={"mobile":390,"tablet":768,"desktop":1440,"wide":1920}
def main():
    output=ROOT/"visual-audit"/"v92-design"
    output.mkdir(parents=True,exist_ok=True)
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),
        functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    rows=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            for name in PAGES:
                for label,width in WIDTHS.items():
                    for theme in ("dark","light"):
                        page=browser.new_page(viewport={"width":width,"height":900})
                        page.add_init_script(f"localStorage.setItem('stockwatch-theme','{theme}')")
                        exceptions=[]
                        page.on("pageerror",lambda e:exceptions.append(str(e)))
                        try:
                            response=page.goto(f"http://127.0.0.1:{server.server_port}/{name}.html",
                                wait_until="domcontentloaded",timeout=25000)
                            if name=="index":
                                page.locator(".sw92-focus-grid").wait_for(timeout=25000)
                                page.locator("#overviewMacro").wait_for(timeout=10000)
                            else:
                                page.locator("main.sw-content").wait_for(timeout=10000)
                            page.wait_for_timeout(500)
                            data=page.evaluate("""() => {
                                const main=document.querySelector('main.sw-content');
                                const box=main?.getBoundingClientRect();
                                const focus=document.querySelector('.sw92-focus-grid');
                                const heat=document.querySelector('.sw-ws-heatmap');
                                const styled=[...document.styleSheets].some(s=>s.href?.includes(
                                    document.body.dataset.page==="index"?
                                    'overview-design-v92.css':'category-design-v92.css'));
                                return {
                                    documentWidth:document.documentElement.scrollWidth,
                                    mainWidth:Math.round(box?.width||0),
                                    mainRight:Math.round(box?.right||0),
                                    stylesheetLoaded:styled,
                                    isFullWidth:!!box&&box.width>0,
                                    focusBeforeHeatmap:focus&&heat?
                                        focus.getBoundingClientRect().top<heat.getBoundingClientRect().top:null,
                                    anyInternalGoals:[...document.querySelectorAll('aside,section,nav')].some(
                                        x=>x.textContent?.includes('Target design level'))
                                };
                            }""")
                            row={"page":name,"viewport":label,"width":width,"theme":theme,
                                 "status":response.status if response else None,**data,
                                 "pageErrors":exceptions}
                            page.screenshot(path=str(output/f"{name}-{label}-{theme}.png"),
                                            animations="disabled",full_page=False)
                            rows.append(row)
                            assert row["status"]==200,row
                            assert row["stylesheetLoaded"],row
                            assert row["isFullWidth"],row
                            assert row["documentWidth"]<=width+2,row
                            assert not row["anyInternalGoals"],row
                            if name=="index":assert row["focusBeforeHeatmap"],row
                            assert not exceptions,exceptions
                        finally:
                            page.close()
            browser.close()
    finally:
        server.shutdown();server.server_close()
        (output/"audit.json").write_text(json.dumps(rows,indent=2),encoding="utf-8")
    print(json.dumps({"captures":len(rows),"output":str(output),"errors":0}))
if __name__=="__main__":main()
