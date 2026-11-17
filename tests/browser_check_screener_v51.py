import functools,http.server,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_port}/"
out=ROOT/"workspace-previews";out.mkdir(exist_ok=True)
try:
 with sync_playwright() as p:
  browser=p.chromium.launch()
  for width in (1440,390):
   page=browser.new_page(viewport={"width":width,"height":950})
   page.route("**/*",lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
   errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
   page.goto(base+"stocks.html")
   page.locator("#stocksRows tr").first.wait_for()
   assert page.locator("#stkCoverage").input_value()=="priced"
   assert page.locator("#stocksRows").get_by_text("Quote not connected").count()==0
   page.locator("#stkSearch").fill("MAERSK A")
   assert page.locator("#stocksRows").get_by_text("A/B observation",exact=False).count()>0
   page.locator("#stkSearch").fill("")
   page.locator("#stkCoverage").select_option("priced")
   page.locator("#stkSessionQuality").select_option("all")
   page.locator('[data-stk-view=heat]').click()
   assert page.locator("#stkHeat .sw-compact-heatgrid").count()==1
   assert page.locator("#stkHeat .sw-heat-cell.positive,#stkHeat .sw-heat-cell.negative").count()>=10
   assert "Map observation date:" in page.locator("#stkHeat").inner_text()
   assert page.locator("#stkHeat").evaluate("(el) => el.scrollWidth <= el.clientWidth + 1")
   assert page.locator(".sw-compact-heatgrid").evaluate("(el) => getComputedStyle(el).gridTemplateColumns.split(' ').length")>=2
   page.screenshot(path=str(out/f"v68-heat-{width}.png"))
   page.locator('[data-stk-view=table]').click()
   page.locator("#stkSessionQuality").select_option("missing")
   page.locator('[data-stk-view=heat]').click()
   assert page.locator("#stkHeat .sw-heat-cell.no-data").count()>0
   assert page.locator("#stkHeat .sw-heat-cell.positive,#stkHeat .sw-heat-cell.negative").count()==0
   page.screenshot(path=str(out/f"v51-heat-{width}.png"))
   page.locator('[data-stk-view=table]').click()
   page.locator(".sw51-columns summary").click()
   page.locator("[data-stk-column='1']").uncheck()
   assert page.locator("#stkTable th").nth(1).is_hidden()
   page.reload()
   page.locator("#stocksRows tr").first.wait_for()
   assert page.locator("#stkTable th").nth(1).is_hidden()
   page.locator("#stkCurrency").select_option("NOK")
   assert page.locator("#stockCount").inner_text()
   assert not errors,errors
   page.screenshot(path=str(out/f"v51-table-{width}.png"))
   page.close()
  browser.close()
finally:server.shutdown()
