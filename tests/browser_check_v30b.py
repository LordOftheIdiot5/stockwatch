import functools,http.server,pathlib,threading,json
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 base=f"http://127.0.0.1:{server.server_port}"
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
   for width in (1440,390):
    for theme in ("dark","light"):
     page=browser.new_page(viewport={"width":width,"height":900})
     page.add_init_script(f"localStorage.setItem('stockwatch-theme','{theme}')")
     errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
     # Fixture verifies integration only; not a real TradingView data test.
     page.route("https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js",lambda route:route.fulfill(content_type="application/javascript",body="/* isolated chart fixture */"))
     page.goto(base+"/company.html?ticker=VOLV-B.ST")
     card=page.locator(".sw-tv-card");card.wait_for()
     assert card.locator("script").count()==0
     card.locator("[data-tv-load]").click()
     def options():return json.loads(card.locator("script").text_content())
     assert options()["symbol"]=="OMXSTO:VOLV_B"
     assert options()["theme"]==theme
     assert "by TradingView" in card.locator(".tradingview-widget-copyright").inner_text()
     page.locator("#swTheme").click()
     page.wait_for_function("JSON.parse(document.querySelector('.sw-tv-card script').textContent).theme===document.body.dataset.theme")
     assert options()["theme"]!=theme
     card.locator("[data-tv-style]").select_option("3")
     assert options()["style"]=="3"
     assert page.locator("#individualChart").count()==1
     assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
     page.unroute("https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js")
     page.route("https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js",lambda route:route.abort())
     card.locator("[data-tv-load]").click()
     card.get_by_text("The chart script could not load.",exact=False).wait_for()
     page.goto(base+"/stocks.html?q=Atlas%20Copco")
     page.locator("#stocksRows .sw-tv-link").first.click()
     page.locator(".sw-tv-card").wait_for()
     assert page.locator("#licensedSeries").count()==1
     page.goto(base+"/price-history.html?listing=ref%3AXOSL%3AEQNR")
     page.locator(".sw-tv-card").wait_for()
     assert page.locator("[data-tv-load]").count()==0
     assert page.locator(".sw-tv-card a").get_attribute("href")=="https://www.tradingview.com/symbols/OSL-EQNR/"
     assert not errors,errors
     page.close()
   browser.close()
 finally:server.shutdown();server.server_close()
if __name__=="__main__":main()
