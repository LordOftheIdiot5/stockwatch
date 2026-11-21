"""V99: empty and actual browser-saved selections, real source-dated prices."""
import functools,http.server,json,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
 server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 results=[]
 try:
  with sync_playwright() as p:
   b=p.chromium.launch(headless=True,args=["--no-sandbox"])
   for width in (390,1440):
    for preset in ("empty","saved"):
     page=b.new_page(viewport={"width":width,"height":900})
     if preset=="saved":
      page.add_init_script("""() => {
        localStorage.setItem('stockwatch-terminal-v31',JSON.stringify({pinned:['AUSS.OL','AFISH.OL'],keys:['fred:DGS10'],days:90}));
        localStorage.setItem('stockwatch-v4-favorites',JSON.stringify(['AFISH.OL']));
      }""")
     else:
      page.add_init_script("""() => {
        localStorage.removeItem('stockwatch-terminal-v31');
        localStorage.removeItem('stockwatch-v4-favorites');
      }""")
     errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
     page.goto(f"http://127.0.0.1:{server.server_port}/index.html",wait_until="domcontentloaded",timeout=30000)
     page.locator("#overviewWatchlist").wait_for(timeout=30000)
     assert page.locator("#overviewWatchTitle").inner_text()=="My watchlist"
     if preset=="empty":
      assert page.locator("#overviewWatchlist [data-watchlist-row]").count()==0
      assert "No saved companies yet" in page.locator("#overviewWatchlist").inner_text()
     else:
      assert page.locator("#overviewWatchlist [data-watchlist-row]").count()==2
      assert page.locator('#overviewWatchlist [data-watchlist-row="AUSS.OL"]').count()==1
      assert page.locator('#overviewWatchlist [data-watchlist-row="AFISH.OL"]').count()==1
      assert "No quantity or market value is assumed" in page.locator("#overviewWatchlist").inner_text()
      assert "Last saved" in page.locator("#overviewWatchlist").inner_text()
      assert page.locator("#overviewWatchlist a[href='stocks.html']").count()==1
      assert page.locator("#overviewWatchlist a[href='terminal.html']").count()==1
     assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+2")
     assert not errors,errors
     (ROOT/"workspace-previews").mkdir(exist_ok=True)
     filename=f"v99-watchlist-{width}-{preset}.png"
     page.screenshot(path=str(ROOT/"workspace-previews"/filename),animations="disabled")
     results.append({"width":width,"preset":preset,"rows":page.locator("#overviewWatchlist [data-watchlist-row]").count(),"errors":errors})
     page.close()
   b.close()
 finally:
  server.shutdown();server.server_close()
  (ROOT/"workspace-previews").mkdir(exist_ok=True)
  (ROOT/"workspace-previews"/"v99-watchlist-audit.json").write_text(json.dumps(results,indent=2))
 print(json.dumps({"views":len(results),"result":"passed"}))
if __name__=="__main__":main()
