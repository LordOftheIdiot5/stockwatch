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
  for width in (1600,1440,390):
   page=browser.new_page(viewport={"width":width,"height":1000})
   page.route("**/*",lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
   errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
   page.goto(base+"terminal.html")
   page.locator("#terminalChart svg").first.wait_for()
   page.locator("#terminalChartMode").select_option("split")
   page.locator("#terminalChartSecond svg").first.wait_for()
   a,b=page.locator("#terminalChart"),page.locator("#terminalChartSecond")
   a.locator('[data-act=in]').click()
   assert a.locator('[data-window]').inner_text()==b.locator('[data-window]').inner_text()
   a.locator("input[type=range]").fill("0")
   assert a.locator(".sw-terminal-inspector").inner_text()[:10]==b.locator(".sw-terminal-inspector").inner_text()[:10]
   if width>1050:
    assert page.locator(".sw-terminal-center").bounding_box()["width"]>page.locator(".sw-terminal-left").bounding_box()["width"]
    page.locator("#terminalFocus").click()
    assert page.locator(".sw-terminal-left").is_hidden()
    page.locator("#terminalFocus").click()
   else:
    page.locator("[data-terminal-view=watch]").click()
    assert page.locator(".sw-terminal-center").is_hidden()
    page.locator("[data-terminal-view=chart]").click()
    assert page.locator(".sw-terminal-center").is_visible()
   assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
   page.screenshot(path=str(out/f"v52-split-{width}.png"))
   page.reload()
   page.locator("#terminalChartSecond svg").first.wait_for()
   assert page.locator("#terminalChartMode").input_value()=="split"
   assert not errors,errors
   page.close()
  browser.close()
finally:server.shutdown()
