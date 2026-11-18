"""Real company UI + native chart interaction; fixture prices are test-only."""
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
   page.goto(base+"company.html?ticker=XNAS%3ANVDA")
   lens=page.locator("#companyEventLens")
   lens.get_by_text("Rolling archive",exact=False).wait_for(timeout=20000)
   assert lens.locator("a[href*='sec.gov/Archives']").count()>0
   lens.locator("select").select_option("strong")
   assert lens.locator("a[href*='sec.gov/Archives']").count()>0
   page.evaluate("""() => {
     const h=document.createElement('div');h.id='testEventChart';document.body.append(h);
     window.testController=window.StockwatchNativeChart.mount(h,{equity:true,bars:[{date:'2026-11-16',close:100},{date:'2026-11-17',close:101}],events:[{date:'2026-11-17',headline:'Test filing',url:'https://example.com/filing',confidence:'strong'},{date:'2026-11-18',headline:'No matching observation',url:'https://example.com/other'}]});
   }""")
   assert page.locator("#testEventChart [data-event-date]").count()==1
   assert page.evaluate("window.testController.inspectDate('2026-11-17')")
   assert "Test filing" in page.locator("#testEventChart [data-chart-events]").inner_text()
   assert not page.evaluate("window.testController.inspectDate('2026-11-18')")
   page.close()
  browser.close()
finally:server.shutdown()
