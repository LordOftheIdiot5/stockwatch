"""Capture real Stockwatch browser screenshots and objective layout diagnostics."""
import argparse
import functools
import http.server
import json
import threading
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGES = {
    "overview": "index.html",
    "stocks": "stocks.html",
    "company": "company.html?ticker=VOLV-B.ST",
    "terminal": "terminal.html",
    "spreads": "spreads.html",
    "shipping": "shipping.html",
    "commodities": "commodities.html",
    "news": "news.html",
    "calendar": "calendar.html",
    "compare": "compare.html",
    "shorts": "shorts.html",
    "intelligence": "intelligence.html",
    "directory": "directory.html",
    "history": "price-history.html",
    "research": "research.html",
    "health": "health.html",
    "welcome": "welcome.html",
    "datasets": "data-products.html",
    "search": "search.html",
}
VIEWPORTS = {"desktop": (1440, 1000), "mobile": (390, 844),
             "small-mobile": (320, 740), "tablet": (768, 1000),
             "wide": (1920, 1080)}
DEFAULT_VIEWPORTS = ("desktop", "mobile")
LAYOUT = """() => {
  const el = document.documentElement;
  const label = document.querySelector('h1');
  const root = document.querySelector('#v4app,#app,main');
  const nav = document.querySelector('.sw-mobile-nav');
  const content = document.querySelector('body[data-page=index] .sw-content');
  const sidebar = document.querySelector('body[data-page=index] .sw-side');
  const w = el.clientWidth;
  const box = content?.getBoundingClientRect();
  const sideBox = sidebar?.getBoundingClientRect();
  const usable = Math.max(1, w - (sideBox?.width || 0));
  const candidates = Array.from(document.querySelectorAll('main h1,main h2,main h3,main button,main input,main select,main a'));
  const overflow = candidates.filter(n => {
    const b=n.getBoundingClientRect(), s=getComputedStyle(n);
    return b.width>0 && b.height>0 && s.visibility!=='hidden' &&
      (b.right>w+2||b.left< -2) && !n.closest('.tablewrap,.sw-table-wrap,[role=dialog]');
  }).slice(0,15).map(n=>({tag:n.tagName,text:n.textContent.trim().slice(0,80),right:Math.round(n.getBoundingClientRect().right)}));
  return {title:document.title,heading:label?.textContent.trim()||null,
    viewport:w,documentWidth:el.scrollWidth,height:el.scrollHeight,
    contentLeftPx:box?Math.round(box.left):null,
    contentRightGapPx:box?Math.round(Math.max(0,w-box.right)):null,
    contentUsableWidthRatio:box?Math.round(1000*box.width/usable)/1000:null,
    horizontalOverflow:el.scrollWidth>w+2,overflowCandidates:overflow,
    mobileNavVisible:!!(nav&&nav.getBoundingClientRect().height>0),
    headings:Array.from(document.querySelectorAll('main h2,main h3')).slice(0,25).map(n=>n.textContent.trim()),
    heatmapTiles:document.querySelectorAll('.sw-heat-cell').length,
    images:Array.from(document.images).filter(n=>n.complete&&!n.naturalWidth).map(n=>n.getAttribute('src')).slice(0,15),
    renderedText:root?.innerText.trim().slice(0,350)||null};
}"""
def capture(base, out, selected, devices, chromium_path=None):
    out.mkdir(parents=True, exist_ok=True)
    records = []
    origin = urlsplit(base).netloc
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium_path)
        for device in devices:
            width, height = VIEWPORTS[device]
            context = browser.new_context(viewport={"width":width,"height":height},
                device_scale_factor=1, is_mobile=device in ("mobile", "small-mobile"), has_touch=device in ("mobile", "small-mobile"))
            # Prevent analytics and unpredictable third-party content. Permit only
            # the audited origin and the public font files used by the site.
            def route(request):
                host = urlsplit(request.request.url).netloc
                if host in (origin, "fonts.googleapis.com", "fonts.gstatic.com"):
                    request.continue_()
                else:
                    request.abort()
            context.route("**/*", route)
            for name in selected:
                page = context.new_page()
                errors, failed, http_errors = [], [], []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("requestfailed", lambda request: failed.append(request.url) if urlsplit(request.url).netloc==origin else None)
                page.on("response", lambda response: http_errors.append({"url":response.url,"status":response.status}) if response.status>=400 and urlsplit(response.url).netloc==origin else None)
                row = {"page":name,"device":device,"url":urljoin(base,PAGES[name]),"screenshots":[]}
                try:
                    response=page.goto(row["url"], wait_until="domcontentloaded", timeout=25000)
                    row["status"]=response.status if response else None
                    try:
                        page.wait_for_function("""() => {
                          const n=document.querySelector('#v4app,#app');
                          return !n || (!n.querySelector('.sw-loading,.loading') && n.innerText.trim().length>20)
                        }""", timeout=12000)
                    except Exception:
                        row["readinessWarning"]="Loading indicator or empty application persisted"
                    try: page.wait_for_load_state("networkidle",timeout=3500)
                    except Exception: pass
                    try: page.evaluate("() => Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,1500))])")
                    except Exception: pass
                    page.wait_for_timeout(300)
                    row.update(page.evaluate(LAYOUT))
                    for suffix,scroll in [("top",0),("middle",max(0,min(row["height"]-height,height))),("bottom",max(0,row["height"]-height))]:
                        if suffix!="top" and (scroll==0 or (suffix=="bottom" and scroll==max(0,min(row["height"]-height,height)))):
                            continue
                        page.evaluate("(y)=>window.scrollTo(0,y)",scroll)
                        page.wait_for_timeout(180)
                        filename=f"{name}-{device}-{suffix}.png"
                        page.screenshot(path=str(out/filename),animations="disabled",timeout=12000)
                        row["screenshots"].append(filename)
                    if name=="overview" and page.locator("#overviewEconomy").count():
                        try:
                            page.locator("#overviewEconomy > summary").click(timeout=5000)
                            page.locator("#overviewMacroPlot svg").wait_for(timeout=12000)
                            page.locator("#overviewMacroPlot").scroll_into_view_if_needed()
                            filename=f"{name}-{device}-macro-lens.png"
                            page.screenshot(path=str(out/filename),animations="disabled",timeout=12000)
                            row["screenshots"].append(filename)
                        except Exception as error:
                            row["interactionWarning"]=str(error)[:2000]
                    if name=="overview" and page.locator("#workspaceHeatExpand").count():
                        try:
                            page.locator("#workspaceHeatExpand").scroll_into_view_if_needed()
                            page.locator("#workspaceHeatExpand").click(timeout=5000)
                            page.locator("#workspaceHeatmap.sw-heat-expanded").wait_for(timeout=5000)
                            extent=page.evaluate("""() => {
                              const outer=document.querySelector('.sw98-market-secondary');
                              const panel=outer?.querySelector(':scope > .sw-ws-heatmap');
                              const inspector=panel?.querySelector('.sw93-heat-inspector');
                              return {grid:outer?.getBoundingClientRect().width||0,
                                      panel:panel?.getBoundingClientRect().width||0,
                                      inspector:inspector?.getBoundingClientRect().width||0};
                            }""")
                            row["expandedHeatmap"]=extent
                            if extent["grid"] and (extent["panel"]<extent["grid"]*0.88 or extent["inspector"]<extent["grid"]*0.82):
                                row["interactionWarning"]="Expanded heatmap leaves excessive unused horizontal space"
                            filename=f"{name}-{device}-expanded-heatmap.png"
                            page.screenshot(path=str(out/filename),animations="disabled",timeout=12000)
                            row["screenshots"].append(filename)
                        except Exception as error:
                            row["interactionWarning"]="Heatmap expansion failed: "+str(error)[:1700]
                    if name=="stocks":
                        page.evaluate("window.scrollTo(0,0)")
                        try:
                            page.locator("[data-stk-view=heat]").click(timeout=3500)
                            page.locator("#stkHeat .sw-heat-cell").first.wait_for(timeout=5000)
                            filename=f"{name}-{device}-heatmap.png"
                            page.locator("#stkHeat").scroll_into_view_if_needed()
                            page.screenshot(path=str(out/filename),animations="disabled",timeout=12000)
                            row["screenshots"].append(filename)
                            row["screenerHeatmapTiles"]=page.locator("#stkHeat .sw-heat-cell").count()
                        except Exception as error:
                            row["interactionWarning"]=str(error)[:2000]
                except Exception as error:
                    row["error"]=str(error).splitlines()[0]
                row.update(pageErrors=errors[:15], failedRequests=failed[:20], httpErrors=http_errors[:20])
                records.append(row)
                page.close()
                print(json.dumps({k:v for k,v in row.items() if k not in ("renderedText","headings","overflowCandidates","screenshots")}),flush=True)
            context.close()
        browser.close()
    (out/"audit.json").write_text(json.dumps({"base":base,"thirdPartyPolicy":"Only audited origin and Google Fonts; other external content blocked","pages":records},indent=2),encoding="utf8")
    return records

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--base-url",help="Optional live public site; otherwise serve this checkout")
    parser.add_argument("--output",default="visual-audit")
    parser.add_argument("--pages",nargs="+",choices=PAGES,default=list(PAGES))
    parser.add_argument("--devices",nargs="+",choices=VIEWPORTS,default=list(DEFAULT_VIEWPORTS))
    parser.add_argument("--chromium-path",help="Optional installed Chromium or Chrome executable")
    args=parser.parse_args()
    server=None
    try:
        if args.base_url:
            base=args.base_url.rstrip("/")+"/"
        else:
            server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
            threading.Thread(target=server.serve_forever,daemon=True).start()
            base=f"http://127.0.0.1:{server.server_port}/"
        records=capture(base,Path(args.output),args.pages,args.devices,args.chromium_path)
        failures=sum(bool(r.get("error") or r.get("status",0)>=400 or r["pageErrors"] or r.get("interactionWarning")) for r in records)
        print(json.dumps({"captures":len(records),"errors":failures,"output":args.output}),flush=True)
        return int(failures>0)
    finally:
        if server:server.shutdown()

if __name__=="__main__":
    raise SystemExit(main())
