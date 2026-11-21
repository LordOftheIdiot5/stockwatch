"""V98 real checkout, desktop/mobile and keyboard: chart-first layout, no synthetic values."""
import functools,http.server,json,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
 server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 evidence=[]
 try:
  with sync_playwright() as p:
   b=p.chromium.launch(headless=True,args=["--no-sandbox"])
   for width in (320,390,768,1024,1440,1920):
    for theme in ("dark","light"):
     page=b.new_page(viewport={"width":width,"height":900})
     page.add_init_script(f"localStorage.setItem('stockwatch-theme','{theme}')")
     errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
     page.goto(f"http://127.0.0.1:{server.server_port}/index.html",wait_until="domcontentloaded",timeout=30000)
     page.locator("#overviewMacroSeries").wait_for(timeout=30000)
     chart=page.locator(".sw98-primary .sw92-focus-chart")
     rail=page.locator(".sw98-intelligence-rail")
     news=page.locator(".sw98-intelligence-rail .sw-overview-news")
     heat=page.locator(".sw98-market-secondary .sw-ws-heatmap")
     assert chart.count()==rail.count()==news.count()==heat.count()==1
     assert chart.bounding_box()["y"]<heat.bounding_box()["y"]
     assert rail.bounding_box()["y"]<heat.bounding_box()["y"]
     if width>=1150:
      assert abs(chart.bounding_box()["y"]-rail.bounding_box()["y"])<=4
      assert chart.bounding_box()["width"]>rail.bounding_box()["width"]
     assert page.locator("#overviewMacroSeries").input_value()=="fx:EUR/NOK"
     assert "NOK per EUR" in page.locator("#overviewMacroPlot").inner_text()
     assert page.locator("#overviewMacroPlot svg").get_attribute("viewBox")=="0 0 640 286"
     assert "Taiwan sources connected" in page.locator("#globalMarketPulse").inner_text()
     index=page.locator("#globalMarketPulse")
     if width<=700:
      assert chart.bounding_box()["y"]<index.bounding_box()["y"]
      assert page.locator(".sw96-source-status").bounding_box()["height"]<175
     else:
      assert index.bounding_box()["y"]<chart.bounding_box()["y"]
     assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
     if width==1440 and theme=="dark":
      page.locator("#overviewMacroSeries").select_option("eia:RBRTE")
      assert "USD/barrel" in page.locator("#overviewMacroPlot").inner_text()
      page.locator("#overviewMacroMode").select_option("delta")
      svg=page.locator("#overviewMacroPlot svg");svg.focus();svg.press("Home")
      assert page.locator("#overviewLensValue").inner_text()=="0"
      svg.press("ArrowRight")
      assert "Observed:" in page.locator("#overviewLensDetail").inner_text()
     assert not errors,errors
     (ROOT/"workspace-previews").mkdir(exist_ok=True)
     filename=f"v98-overview-{width}-{theme}.png"
     page.screenshot(path=str(ROOT/"workspace-previews"/filename),animations="disabled")
     evidence.append({"width":width,"theme":theme,"chartWidth":round(chart.bounding_box()["width"]),"railWidth":round(rail.bounding_box()["width"]),"screenshot":filename})
     page.close()
   b.close()
 finally:
  server.shutdown();server.server_close()
  (ROOT/"workspace-previews").mkdir(exist_ok=True)
  (ROOT/"workspace-previews"/"v98-overview-audit.json").write_text(json.dumps(evidence,indent=2))
 print(json.dumps({"views":len(evidence),"result":"passed"}))
if __name__=="__main__": main()
