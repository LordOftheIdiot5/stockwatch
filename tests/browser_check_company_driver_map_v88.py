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
   page.goto(base+"company.html?ticker=NHY.OL")
   map=page.locator("#companyDriverMap")
   map.locator("[data-driver-node=prices]").wait_for()
   assert map.locator("[data-driver-node]").count()==6
   for key in ("numbers","prices","operations","potential","attention","risk"):
    b=map.locator("[data-driver-node="+key+"]")
    b.click()
    assert b.get_attribute("aria-pressed")=="true"
    assert map.locator("#sw88-driver-detail h3").inner_text().startswith(b.locator("strong").inner_text())
   map.locator("[data-driver-node=operations]").click()
   assert map.get_by_role("button",name="Reported ownership & assets").count()==1
   assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
   assert not errors,errors
   (ROOT/"workspace-previews").mkdir(exist_ok=True)
   map.screenshot(path=str(ROOT/"workspace-previews"/f"v88-driver-map-{width}.png"))
   page.close()
  browser.close()
finally:server.shutdown()
