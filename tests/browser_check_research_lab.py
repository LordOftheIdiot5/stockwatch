import functools,http.server,pathlib,threading
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
   for w in (1600,390):
    page=browser.new_page(viewport={"width":w,"height":940})
    errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{server.server_port}/terminal.html")
    page.locator("#labHeat .sw-lab-tiles a").first.wait_for()
    page.locator("#labMinMove").fill("2")
    assert "matches" in page.locator("#labScreen").inner_text()
    page.locator("[data-lab-tab='1']").click()
    page.locator("#labGraphA svg").wait_for()
    page.locator("#labGraphB svg").wait_for()
    chart=page.locator("#labGraphA")
    full=chart.locator("[data-chart-window]").inner_text()
    other=page.locator("#labGraphB [data-chart-window]").inner_text()
    chart.get_by_role("button",name="Zoom in").click()
    assert chart.locator("[data-chart-window]").inner_text()!=full
    assert page.locator("#labGraphB [data-chart-window]").inner_text()==other
    chart.get_by_role("button",name="Pan earlier").click()
    chart.get_by_role("slider",name="Inspect observation").fill("0")
    chart.get_by_role("button",name="Reset").click()
    assert chart.locator("[data-chart-window]").inner_text()==full
    page.locator("#labIndicator").select_option("rsi")
    page.locator("#labIndicatorGraph svg").wait_for()
    page.locator("[data-lab-tab='2']").click()
    page.locator("#labCompany").select_option("NOVO-B.CO")
    assert "Q3 2026" in page.locator("#labFacts").inner_text()
    for key,val in {"labFCF":"100","labGrowth":"0","labDiscount":"10","labTG":"0","labDebt":"100","labShares":"10"}.items():page.locator("#"+key).fill(val)
    page.locator("#labDCF").click()
    assert "Value per share" in page.locator("#labDCFResult").inner_text()
    page.locator("[data-lab-tab='3']").click()
    page.locator("#labPairResult .sw-lab-metrics").wait_for()
    page.locator("#labBacktest").click()
    assert "Authorized equity history required" in page.locator("#labBackResult").inner_text()
    page.locator("[data-lab-tab='4']").click()
    page.locator("#labContext").select_option("NOVO-B.CO")
    assert "Connected research context" in page.locator("#labContextBox").inner_text()
    page.locator("[data-lab-tab='5']").click()
    page.locator("#labAlertTicker").select_option("NOVO-B.CO")
    page.locator("#labAlertValue").fill("1")
    page.locator("#labAddAlert").click()
    assert "Novo Nordisk" in page.locator("#labAlerts").inner_text()
    page.locator("#labAsk").fill("oil")
    assert "Brent" in page.locator("#labEvidence").inner_text()
    page.locator("#swTheme").click()
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    assert not errors,errors
    page.reload();page.locator("#labAlerts").wait_for();assert "Novo Nordisk" in page.locator("#labAlerts").inner_text()
    page.close()
   browser.close()
 finally:server.shutdown();server.server_close()
if __name__=="__main__":main()
