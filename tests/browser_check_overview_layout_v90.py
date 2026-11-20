"""V90 screenshot-based desktop width and mobile usability checkpoint.

Requires installed Playwright & Chromium, separate from static unittest. It reads
real CSS bounding boxes, captures dark/light views, and does not fake market data.
"""
import functools
import http.server
import json
from pathlib import Path
import threading
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
SIZES={"small-mobile":320,"mobile":390,"tablet":768,"desktop":1440,"wide":1920}

def main():
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(
        http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    out=ROOT/"visual-audit"/"v90-layout"
    out.mkdir(parents=True,exist_ok=True)
    observations=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            for width_name,width in SIZES.items():
                for theme in ("dark","light"):
                    page=browser.new_page(viewport={"width":width,"height":900})
                    page.add_init_script(f"localStorage.setItem('stockwatch-theme','{theme}')")
                    problems=[]
                    page.on("pageerror",lambda error: problems.append(str(error)))
                    page.goto(f"http://127.0.0.1:{server.server_port}/index.html",
                              wait_until="domcontentloaded",timeout=25000)
                    page.wait_for_timeout(1200)
                    results=page.evaluate("""() => {
                      const main=document.querySelector('main.sw-content');
                      const sidebar=document.querySelector('.sw-side');
                      const skip=document.querySelector('.sw-skip-content-v90');
                      const rect=main?.getBoundingClientRect();
                      const navWidth=window.innerWidth>1050 ? sidebar?.getBoundingClientRect().width||0 : 0;
                      return {width:window.innerWidth,theme:document.body.dataset.theme,
                        mainWidth:Math.round(rect?.width||0),
                        rightGap:Math.round(window.innerWidth-(rect?.right||0)),
                        coverage:(rect?.width||0)/(window.innerWidth-navWidth),
                        documentWidth:document.documentElement.scrollWidth,
                        navLinkCount:document.querySelectorAll('.sw-nav .sw-link').length,
                        skipLink:!!skip && !!document.querySelector('#main-content'),
                        heatmapPresent:!!document.querySelector('#v4app'),
                        cssLoaded:[...document.styleSheets].some(s=>s.href?.includes('overview-ux-v90.css'))};
                    }""")
                    results["errors"]=problems
                    results["viewportName"]=width_name
                    filename=f"{width_name}-{theme}.png"
                    page.screenshot(path=str(out/filename),full_page=False,
                                    animations="disabled")
                    results["screenshot"]=filename
                    observations.append(results)
                    assert results["cssLoaded"],results
                    assert results["skipLink"],results
                    assert results["navLinkCount"]>=12,results
                    assert results["documentWidth"]<=width+2,results
                    if width>=1440:
                        assert results["coverage"]>=.93,results
                        assert results["rightGap"]<=48,results
                    assert results["theme"]==theme,results
                    assert not problems,problems
                    page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        (out/"audit.json").write_text(json.dumps(observations,indent=2),encoding="utf-8")
    print(json.dumps({"views":len(observations),"status":"passed",
                      "screenshots":str(out)},indent=2))

if __name__=="__main__":main()
