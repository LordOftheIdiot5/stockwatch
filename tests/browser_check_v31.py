import functools,http.server,pathlib,threading
from playwright.sync_api import sync_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
   for width in (1600,390):
    page=browser.new_page(viewport={"width":width,"height":950})
    errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{server.server_port}/terminal.html")
    page.locator("#terminalChart svg").wait_for()
    if width<=1050:page.locator("[data-terminal-view=watch]").click()
    page.locator("#terminalEquities").wait_for()
    page.locator("#terminalQuery").fill("Novo Nordisk")
    page.locator("[data-terminal-ticker='NOVO-B.CO']").click()
    if width<=1050:page.locator("[data-terminal-view=chart]").click()
    assert "Novo Nordisk" in page.locator("#terminalInstrument").inner_text()
    page.locator("#terminalPin").click()
    if width<=1050:page.locator("[data-terminal-view=watch]").click()
    page.locator("#terminalWatch").check()
    assert page.locator("#terminalEquities [data-terminal-ticker]").count()==1
    if width<=1050:page.locator("[data-terminal-view=chart]").click()
    page.locator("#terminalMode").select_option("raw")
    page.locator("#terminalChart svg").wait_for()
    page.locator("[data-terminal-days='30']").click()
    page.locator("#terminalChart input").fill("0")
    assert page.locator("#terminalChart .sw-terminal-inspector").inner_text()
    page.locator("#swTheme").click()
    assert page.locator("body").get_attribute("data-theme")=="light"
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
    page.reload()
    page.locator("#terminalPin").wait_for()
    assert "Saved" in page.locator("#terminalPin").inner_text()
    assert not errors,errors
    page.screenshot(path=str(ROOT/"workspace-previews"/f"v31-terminal-{width}.png"),full_page=True)
    page.close()
   browser.close()
 finally:server.shutdown();server.server_close()
if __name__=="__main__":
 (ROOT/"workspace-previews").mkdir(exist_ok=True)
 main()
