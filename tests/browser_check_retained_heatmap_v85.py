"""Map continuity during complete scanner refresh failure; no network data fetched."""
import functools,http.server,json,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/"data/signals.json").read_text())
# Select the real broad dated snapshot, then simulate a complete later failure.
counts={}
for r in data["companies"]:
    if isinstance(r.get("changePct"),(float,int)) and (r.get("volume") or 0)>0 and (r.get("close") or 0)>0 and r.get("currency") and r.get("date"):
        counts[r["date"]]=counts.get(r["date"],0)+1
day=max(d for d,n in counts.items() if n>=10)
expected=counts[day]
for row in data["companies"]:
    row["priceStatus"]="retained"
    row["excessSigma"]=None
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_port}/"
try:
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width in (1440,390):
            page=browser.new_page(viewport={"width":width,"height":900})
            page.route("**/*",lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
            page.route("**/data/signals.json*",lambda r:r.fulfill(json=data))
            errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            selector=".sw-heat-cell.positive,.sw-heat-cell.negative,.sw-heat-cell.flat"
            page.goto(base+"index.html")
            page.locator("#workspaceHeatmap .sw-heat-cell").first.wait_for()
            assert page.locator(".sw-overview-coverage").count()==0
            assert page.locator("#overviewEvents").get_attribute("open") is not None
            assert page.locator("#workspaceHeatmap").locator(selector).count()==expected
            assert str(expected)+" with changes" in page.locator("#workspaceHeatCount").inner_text()
            page.goto(base+"stocks.html")
            page.locator("#stocksRows tr").first.wait_for()
            button=page.locator("[data-stk-view=heat]")
            assert button.count()==1
            # Test the real control, not a forced click or DOM event.
            button.click(timeout=5000)
            assert button.get_attribute("aria-pressed")=="true"
            assert page.locator("#stkHeat").locator(selector).count()==expected
            page.locator("#stkSessionQuality").select_option("comparable")
            assert page.locator("#stkHeat").locator(selector).count()==0
            page.goto(base+"health.html")
            page.locator("#marketCoverage .sw-overview-coverage").wait_for()
            assert "Priced listings with moves" in page.locator("#marketCoverage").inner_text()
            assert "Research listings" in page.locator("#marketCoverage").inner_text()
            assert not errors,errors
            page.close()
        browser.close()
    print(json.dumps({"date":day,"expected":expected,"views":4,"outage":"all retained","strict_signals":0}))
finally:
    server.shutdown()
