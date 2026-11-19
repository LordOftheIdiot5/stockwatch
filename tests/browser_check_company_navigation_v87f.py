"""Search and legacy Hydro routes retain the primary Stockwatch shell."""
import functools,http.server,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_port}/"
try:
 with sync_playwright() as p:
  browser=p.chromium.launch()
  for width in (1440,390):
   page=browser.new_page(viewport={"width":width,"height":900})
   page.route("**/*",lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
   errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
   page.goto(base+"index.html")
   page.locator("#workspaceHeatmap .sw-heat-cell").first.wait_for()
   pending=page.locator("#workspacePending a[href='company.html?ticker=NHY.OL']")
   if pending.count():
    page.locator("#workspacePending summary").click()
    assert pending.is_visible()
   page.locator("#swGlobalSearch").fill("hydro")
   link=page.locator("#swQuickResults a[href='company.html?ticker=NHY.OL']")
   assert link.count()==1
   link.click()
   page.locator(".sw-company-heading h2").get_by_text("Norsk Hydro").wait_for()
   assert page.locator(".sw-side").count()==1 and page.locator(".sw-mobile-nav").count()==1
   page.get_by_text("Reported corporate ownership & assets").wait_for()
   page.goto(base+"research.html?instrument=XOSL%3ANHY#targetDetail")
   page.wait_for_url("**/company.html?ticker=NHY.OL")
   page.locator(".sw-company-heading h2").get_by_text("Norsk Hydro").wait_for()
   page.goto(base+"research.html?instrument=XOSL%3ANHY&mapping=1#targetDetail")
   page.locator("#targetDetail").get_by_text("Norsk Hydro",exact=True).wait_for()
   page.goto(base+"company.html?ticker=ref%3AXOSL%3ANHY")
   page.locator(".sw-company-heading h2").get_by_text("Norsk Hydro").wait_for()
   page.goto(base+"stocks.html?q=NHY")
   page.locator("#stocksRows").get_by_text("Norsk Hydro",exact=True).wait_for()
   assert page.locator("#stocksRows [data-stock='NHY.OL']").count()==1
   assert not errors,errors
   page.close()
  browser.close()
finally:server.shutdown()
