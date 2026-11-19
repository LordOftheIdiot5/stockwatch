"""Browser interaction using an explicitly synthetic test-only attention snapshot."""
import functools,http.server,threading,json
from pathlib import Path
from datetime import date,timedelta
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
days=[{"date":str(date(2026,11,5)+timedelta(days=i)),"issuer":2 if i==13 else 0,"media":3 if i==1 else 0} for i in range(14)]
fixture={"schemaVersion":1,"generated":"2026-11-19T02:00:00Z","windowStart":days[0]["date"],"windowEnd":days[-1]["date"],"listings":{"NHY.OL":{"listingId":"NHY.OL","daily":days,"observedRecords":5,"potential":[{"id":"test","headline":"Test contract announcement","topic":"Contracts / agreements","evidence":"issuer","published":"2026-11-18T12:00:00Z","url":"https://example.com/test-only"}]}}}
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_port}/"
try:
 with sync_playwright() as p:
  browser=p.chromium.launch()
  for width in (1440,390):
   page=browser.new_page(viewport={"width":width,"height":900})
   errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
   def route(r):
    if r.request.url.split("?")[0]==base+"data/driver-attention-v1.json":r.fulfill(status=200,content_type="application/json",body=json.dumps(fixture))
    elif r.request.url.startswith(base):r.continue_()
    else:r.abort()
   page.route("**/*",route)
   page.goto(base+"company.html?ticker=NHY.OL")
   m=page.locator("#companyDriverMap")
   m.locator("[data-driver-node=attention]").click(timeout=20000)
   box=m.locator(".sw88-attention")
   box.get_by_text("Observed news attention",exact=True).wait_for()
   assert box.locator(".sw88-attention-day").count()==14
   assert box.get_by_text("2 retained records",exact=True).count()==1
   assert "No hype or sentiment score." in box.inner_text()
   m.locator("[data-driver-node=potential]").click()
   box.get_by_role("link",name="Test contract announcement").wait_for()
   assert box.get_by_role("link",name="Test contract announcement").get_attribute("href")=="https://example.com/test-only"
   assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
   page.goto(base+"company.html?ticker=XNAS%3ANVDA")
   m.locator("[data-driver-node=attention]").click(timeout=20000)
   m.get_by_text("No archive attention snapshot available",exact=False).wait_for()
   assert not errors,errors
   page.close()
  browser.close()
finally:server.shutdown()
