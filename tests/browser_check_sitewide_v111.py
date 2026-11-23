"""V111 release gate: real rendered Overview and all inner routes.

Exercise the heatmap expansion and prove it uses the available dashboard width,
then check every customer route at desktop and key journeys on mobile. Fixtures
are the actual repo data; no invented market observations or network mock prices.
"""
import functools
import http.server
import pathlib
import threading
from playwright.sync_api import sync_playwright

ROOT=pathlib.Path(__file__).resolve().parents[1]
ROUTES={
 "overview":"index.html",
 "terminal":"terminal.html",
 "stocks":"stocks.html",
 "company":"company.html?ticker=NHY.OL",
 "compare":"compare.html",
 "news":"news.html",
 "calendar":"calendar.html",
 "spreads":"spreads.html",
 "shipping":"shipping.html",
 "commodities":"commodities.html",
 "shorts":"shorts.html",
 "intelligence":"intelligence.html",
 "search":"search.html",
 "directory":"directory.html",
 "history":"price-history.html",
 "health":"health.html",
 "datasets":"data-products.html",
 "research":"research.html",
 "welcome":"welcome.html",
}
MOBILE=("overview","company","stocks","terminal","compare","news","calendar",
        "spreads","shipping","commodities","history","health","directory",
        "research","search","intelligence")

def assert_page(page,route,width,base):
    errors=[]
    page.on("pageerror",lambda err:errors.append(str(err)))
    response=page.goto(base+ROUTES[route],wait_until="domcontentloaded",timeout=25000)
    assert response and response.status==200,(route,response.status if response else None)
    page.locator("link[href*='sitewide-polish-v111.css']").wait_for(state="attached",timeout=5000)
    page.locator("body").wait_for()
    # Some pages are brand-only: their H1s are outside of the JS workspace.
    assert page.locator("h1").count()>=1,(route,"missing page heading")
    page.wait_for_timeout(250)
    dims=page.evaluate("""() => {
      const html=document.documentElement, link=document.querySelector("link[href*='sitewide-polish-v111.css']");
      return {scroll:html.scrollWidth,client:html.clientWidth,
        loaded:!!link?.sheet,
        bodyText:(document.body.innerText||"").length};
    }""")
    assert dims["loaded"],(route,"V111 stylesheet not loaded")
    assert dims["bodyText"]>60,(route,"empty page")
    if dims["scroll"]>dims["client"]+3:
        suspects=page.evaluate("""() => [...document.querySelectorAll('body *')]
          .filter(el=>{const box=el.getBoundingClientRect(), style=getComputedStyle(el);
            return box.width>8&&box.height>4&&box.right>innerWidth+3&&
              style.display!=='none'&&style.visibility!=='hidden';})
          .map(el=>{const r=el.getBoundingClientRect();return {
            tag:el.tagName,id:el.id,cls:String(el.className).slice(0,90),
            x:Math.round(r.x),right:Math.round(r.right),width:Math.round(r.width),
            minWidth:getComputedStyle(el).minWidth,
            scrollWidth:el.scrollWidth,clientWidth:el.clientWidth};})
          .sort((a,b)=>b.right-a.right).slice(0,30)""")
        print("WIDTH_OFFENDERS",route,width,suspects,flush=True)
    assert dims["scroll"]<=dims["client"]+3,(route,width,"page-level overflow",dims)
    # A route error is not acceptable because an apparent loading placeholder
    # can otherwise mask a broken data hydration pipeline.
    assert not errors,(route,"JavaScript page errors",errors[:3])
    return dims

def main():
    server=http.server.ThreadingHTTPServer(
        ("127.0.0.1",0),
        functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT))
    )
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}/"
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            try:
                for width,routes in ((1440,ROUTES),(390,MOBILE)):
                    ctx=browser.new_context(viewport={"width":width,"height":900},
                        device_scale_factor=1,has_touch=(width==390))
                    try:
                        for route in routes:
                            page=ctx.new_page()
                            try:assert_page(page,route,width,base)
                            finally:page.close()
                        print(f"V111 all-routes {width}px pass: {len(routes)} routes",flush=True)
                    finally:ctx.close()
                for width in (1440,1920):
                    ctx=browser.new_context(viewport={"width":width,"height":1080},
                        device_scale_factor=1)
                    try:
                        page=ctx.new_page()
                        assert_page(page,"overview",width,base)
                        page.locator("#overviewMacroPlot svg.sw-overview-chart-svg").wait_for(timeout=15000)
                        box=page.locator("#overviewMacroPlot svg.sw-overview-chart-svg").bounding_box()
                        chart_ratio=box["width"]/max(box["height"],1)
                        assert 2.12<=chart_ratio<=2.36,(width,"Chart is letterboxed by a fixed height",box)
                        page.locator("#workspaceHeatExpand").wait_for(timeout=15000)
                        page.locator("#workspaceHeatmap .sw-heat-cell").first.wait_for(timeout=15000)
                        page.locator("#workspaceHeatExpand").click()
                        assert page.locator("#workspaceHeatmap").evaluate("(e)=>e.classList.contains('sw-heat-expanded')")
                        measures=page.evaluate("""() => {
                          const grid=document.querySelector(".sw98-market-secondary");
                          const heat=grid?.querySelector(":scope > .sw-ws-heatmap");
                          const inspector=heat?.querySelector(".sw93-heat-inspector");
                          const col=grid?.getBoundingClientRect(),tile=heat?.getBoundingClientRect();
                          const insp=inspector?.getBoundingClientRect();
                          return {grid:col?.width,heat:tile?.width,inspector:insp?.width,
                            columns:window.getComputedStyle(grid).gridTemplateColumns};
                        }""")
                        assert measures["heat"]>=measures["grid"]*0.9,(width,measures)
                        assert measures["inspector"]>=measures["grid"]*0.85,(width,measures)
                        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+3"),(width,"map expanded page overflow")
                        print(f"V111 expanded heatmap width {width}px: {measures}",flush=True)
                    finally:
                        ctx.close()
            finally:browser.close()
    finally:server.shutdown();server.server_close()

if __name__=="__main__":main()
