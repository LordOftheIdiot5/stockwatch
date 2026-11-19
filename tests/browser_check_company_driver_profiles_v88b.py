import functools,http.server,threading
from pathlib import Path
from urllib.parse import quote
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
   for ticker,label in [("NHY.OL","Aluminium & electricity"),("FRO.OL","Tanker charter earnings"),("ref:XOSL:MOWI","Salmon & feed prices"),("XNAS:NVDA","Product mix & input costs")]:
    page.goto(base+"company.html?ticker="+quote(ticker,safe=""))
    m=page.locator("#companyDriverMap")
    m.locator("[data-driver-node=prices] small",has_text=label).wait_for(timeout=20000)
    m.locator("[data-driver-node=prices]").click()
    assert m.get_by_text("Issuer evidence",exact=False).count()>0
    m.locator("[data-driver-node=numbers]").click()
    assert m.get_by_text("reported period example",exact=False).count()==1
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    (ROOT/"workspace-previews").mkdir(exist_ok=True)
    m.screenshot(path=str(ROOT/"workspace-previews"/f"v88b-{ticker.replace(':','-')}-{width}.png"))
   page.close()
  browser.close()
finally:server.shutdown()
