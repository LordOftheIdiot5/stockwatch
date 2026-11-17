import functools,http.server,pathlib,threading
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as p:
   b=p.chromium.launch(headless=True,args=["--no-sandbox"])
   for width in (1440,390):
    for theme in ("dark","light"):
     page=b.new_page(viewport={"width":width,"height":900})
     page.add_init_script(f"localStorage.setItem('stockwatch-theme','{theme}')")
     errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
     page.goto(f"http://127.0.0.1:{server.server_port}/index.html")
     page.locator("#overviewMacroSeries").wait_for(timeout=25000)
     assert "Market overview" in page.locator(".sw-overview-head").inner_text()
     assert page.locator(".sw-ws-pulse-grid").bounding_box()["y"] < page.locator(".sw-overview-workbench").bounding_box()["y"]
     assert page.locator(".sw-attention-panel").bounding_box()["y"] < page.locator(".sw-overview-workbench").bounding_box()["y"]
     assert page.locator("#overviewMacroPlot svg").count()==1
     page.locator("#overviewMacroSeries").select_option("fred:DGS10")
     page.locator("#overviewMacroRange").select_option("365")
     assert "percent" in page.locator("#overviewMacroPlot").inner_text().lower()
     assert page.locator("#workspaceCoverage").count()==1
     page.locator("#workspaceCoverage").select_option("observed")
     assert page.locator(".sw-heat-cell.no-data").count()==0
     assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
     assert not errors,errors
     (ROOT/"workspace-previews").mkdir(exist_ok=True)
     page.screenshot(path=str(ROOT/"workspace-previews"/f"modern-overview-{width}-{theme}.png"))
     page.close()
   b.close()
 finally:server.shutdown();server.server_close()
if __name__=="__main__":main()
