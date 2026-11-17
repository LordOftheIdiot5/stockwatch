"""Read-only live site audit; screenshots, geometry and DOM facts, no licensed raw price exports."""
import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
BASE="https://stocks.nordl.dev/"
PAGES=["index.html","welcome.html","stocks.html","company.html","compare.html","terminal.html","directory.html","research.html","intelligence.html","price-history.html","spreads.html","news.html","calendar.html","shorts.html","commodities.html","shipping.html","health.html"]
OUT=Path("live-layout-report")
OUT.mkdir(exist_ok=True)
JS=r"""() => {
const visible=e=>{let b=e.getBoundingClientRect(),s=getComputedStyle(e);return b.width>0&&b.height>0&&s.visibility!=='hidden'&&s.display!=='none'};
const rect=e=>{let b=e.getBoundingClientRect();return {x:Math.round(b.x),y:Math.round(b.y),w:Math.round(b.width),h:Math.round(b.height)}};
const nav=[...document.querySelectorAll('nav a')].filter(visible).map(e=>e.innerText.trim()).filter(Boolean).slice(0,35);
const headings=[...document.querySelectorAll('h1,h2,h3')].filter(visible).map(e=>({text:e.innerText.trim().slice(0,140),tag:e.tagName,...rect(e)})).slice(0,30);
const overflow=[...document.querySelectorAll('main,main section,main h1,main h2,main a,main button,header,nav,aside,table')].filter(visible).filter(e=>{let b=e.getBoundingClientRect();return (b.x< -2||b.right>innerWidth+2)&&!e.closest('[style*="overflow"],.table-wrap,.table-scroll')}).slice(0,16).map(e=>({tag:e.tagName,cls:e.className?.toString().slice(0,80),text:e.innerText?.trim().slice(0,60),...rect(e)}));
const body=document.body.innerText;
const status=body.split('\n').map(x=>x.trim()).filter(x=>/loading|unavailable|no data|no results|no observations|not connected|not available|stale|coverage|licen[cs]/i.test(x)).slice(0,20).map(x=>x.slice(0,160));
return {title:document.title,viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyHeight:document.documentElement.scrollHeight,headings,nav,overflow,status,canvasCount:document.querySelectorAll('canvas').length,tableCount:document.querySelectorAll('table').length,buttons:[...document.querySelectorAll('button')].filter(visible).length,stylesheets:[...document.styleSheets].map(s=>s.href).filter(Boolean).map(x=>new URL(x).pathname),theme:getComputedStyle(document.body).backgroundColor};
}"""
async def inspect(browser,path,width,height,gate):
    async with gate:
        page=await browser.new_page(viewport={"width":width,"height":height},reduced_motion="reduce",device_scale_factor=1)
        errors=[];failed=[]
        page.on("pageerror",lambda e:errors.append(str(e)[:200]))
        page.on("response",lambda r:failed.append({"status":r.status,"url":r.url.split("?")[0]}) if r.status>=400 else None)
        slug=path.split("?")[0].replace(".html","")
        data={"path":path,"width":width}
        try:
            r=await page.goto(BASE+path,wait_until="load",timeout=30000)
            try:await page.evaluate("document.fonts.ready")
            except Exception:pass
            try:await page.wait_for_load_state("networkidle",timeout=5000)
            except Exception:pass
            await page.wait_for_timeout(700)
            data.update(await page.evaluate(JS))
            data["http"]=r.status if r else None
            data["finalUrl"]=page.url
            await page.screenshot(path=str(OUT/f"{slug}-{width}.png"),animations="disabled",timeout=15000)
            if width==1440 and data.get("bodyHeight",0)>height and data["bodyHeight"]<9000:
                await page.screenshot(path=str(OUT/f"{slug}-{width}-full.png"),full_page=True,animations="disabled",timeout=15000)
        except Exception as e:data["error"]=str(e)[:350]
        finally:
            data["errors"]=errors;data["failedResponses"]=failed[:15]
            await page.close()
        print("AUDIT "+json.dumps({k:data.get(k) for k in ("path","width","http","scrollWidth","bodyHeight","error","errors","failedResponses")}),flush=True)
        return data
async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        gate=asyncio.Semaphore(4)
        # Company detail needs a real selection; use an existing monitored ticker.
        paths=[("company.html?ticker=SALM.OL" if x=="company.html" else x) for x in PAGES]
        tasks=[inspect(browser,path,w,h,gate) for path in paths for w,h in [(1440,1000),(390,844)]]
        results=await asyncio.gather(*tasks)
        await browser.close()
    (OUT/"report.json").write_text(json.dumps(results,indent=2),encoding="utf8")
    print("AUDIT_SUMMARY "+json.dumps({"pages":len(PAGES),"captures":len(results),"http200":sum(x.get("http")==200 for x in results),"failures":sum(bool(x.get("error")) for x in results)}),flush=True)
if __name__=="__main__":asyncio.run(main())
