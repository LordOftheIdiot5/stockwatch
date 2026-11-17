"""Real browser interaction checks. Artificial OHLC exists only in this ephemeral fixture."""
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
        for width,height in [(1440,1000),(390,844)]:
            page=browser.new_page(viewport={"width":width,"height":height},reduced_motion="reduce")
            page.route("**/*",lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
            errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
            page.goto(base+"terminal.html",wait_until="load")
            page.locator("#terminalChart .sw49-plot svg").wait_for()
            real=page.locator("#terminalChart")
            assert real.locator('[data-act="candles"]').is_disabled()
            real.locator('[data-act="in"]').click()
            assert real.locator("[data-window]").inner_text()
            page.screenshot(path=str(out/f"v49-terminal-{width}.png"))
            page.evaluate("""()=>{
              const host=document.createElement('section');host.id='testfixture';host.style.cssText='max-width:900px;margin:12px auto;padding:12px;background:var(--sw-surface)';
              document.body.replaceChildren(host);
              const rows=Array.from({length:60},(_,i)=>{const c=100+i*.4+Math.sin(i)*2;return {date:new Date(Date.UTC(2026,0,1+i)).toISOString().slice(0,10),open:c-.5,high:c+1,low:c-1,close:c,volume:1000+i*10}});
              window.StockwatchNativeChart.mount(host,{label:'TEST FIXTURE — not market data',bars:rows,equity:true,unit:'fixture'});
            }""")
            host=page.locator("#testfixture")
            assert host.locator("[data-candle]").count()==60
            assert host.locator("[data-volume]").count()==60
            host.locator('[data-act="sma"]').click()
            host.locator('[data-act="ema"]').click()
            host.locator('[data-act="rsi"]').click()
            assert host.locator(".sw49-rsi svg").is_visible()
            host.locator('[data-act="in"]').click()
            assert 0<host.locator("[data-candle]").count()<60
            host.locator('[data-act="reset"]').click()
            assert host.locator("[data-candle]").count()==60
            host.locator('[data-act="horizontal"]').click()
            host.locator(".sw49-plot").click(position={"x":80,"y":65})
            assert host.locator('line[stroke="#ecc37a"][stroke-dasharray="5 3"]').count()==1
            host.locator('[data-act="clear"]').click()
            assert host.locator('line[stroke="#ecc37a"][stroke-dasharray="5 3"]').count()==0
            host.locator('[data-act="line"]').click()
            assert host.locator("[data-candle]").count()==0
            host.locator('[data-act="candles"]').click()
            host.locator("input").fill("0")
            assert "2026-01-01" in host.locator(".sw-terminal-inspector").inner_text()
            assert not errors,errors
            page.screenshot(path=str(out/f"v49-fixture-{width}.png"))
            page.close()
        browser.close()
finally:
    server.shutdown()
