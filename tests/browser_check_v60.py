"""Combined candidate quality audit. Captures all cases even if individual checks fail."""
import functools,http.server,json,threading,time
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
PAGES="index stocks company compare terminal directory research intelligence price-history spreads news calendar shorts commodities shipping health welcome search data-products".split()
VIEWPORTS=[(1440,1000),(768,1024),(390,844),(320,800)]
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(QuietHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
base=f"http://127.0.0.1:{server.server_port}/"
out=ROOT/"workspace-previews";out.mkdir(exist_ok=True)
report=[];interaction=[]
def check_interactions(browser):
    page=browser.new_page(viewport={"width":1440,"height":1000},accept_downloads=True)
    page.route("**/*",lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
    errors=[];page.on("pageerror",lambda e:errors.append(str(e)))
    def run(name,fn):
        errors.clear()
        try:
            fn()
            assert not errors,errors
            interaction.append({"name":name,"passed":True})
        except Exception as e:interaction.append({"name":name,"passed":False,"error":str(e)[:1200]})
    def search():
        page.goto(base+"search.html?q=SALM.OL&kind=Company")
        page.locator('.gs-result').first.wait_for()
        assert "SalMar" in page.locator('.gs-result').first.inner_text()
        page.locator('input[name=q]').fill('zzzz-no-matching-company')
        assert page.locator('.gs-result').count()==0
        page.locator('input[name=q]').fill('Orsted')
        page.locator('.gs-result').first.wait_for()
        assert "rsted" in page.locator('.gs-result').first.inner_text().lower()
    def portal():
        page.goto(base+"data-products.html")
        page.locator('.dp-product').first.wait_for()
        assert page.locator('.dp-product').count()==8
        page.locator('.dp-product summary').first.click()
        assert "not an active API contract" in page.locator('.dp-product details').first.inner_text()
        with page.expect_download() as download:
            page.locator('#dpExport').click()
        data=json.loads(Path(download.value.path()).read_text())
        assert len(data['products'])==8 and all('commercialStatus' in x for x in data['products'])
        assert all('observations' not in x and 'bars' not in x for x in data['products'])
    def workspaces():
        page.goto(base+"terminal.html")
        page.locator('.sw59-workspaces summary').click()
        page.locator('#terminalChartMode').select_option('split')
        page.locator('#sw59Name').fill('Test split')
        page.locator('#sw59Save').click()
        assert 'Test split' in page.locator('#sw59Select').inner_text()
        page.locator('#terminalChartMode').select_option('overlay')
        page.locator('#sw59Load').click()
        assert page.locator('#terminalChartMode').input_value()=='split'
        page.reload()
        page.locator('.sw59-workspaces summary').click()
        assert 'Test split' in page.locator('#sw59Select').inner_text()
        assert page.locator('#terminalChartMode').input_value()=='split'
    def voyage():
        page.goto(base+"shipping.html")
        page.locator('.sw56-inputs input').first.wait_for()
        vals=dict(ladenMiles=2400,ballastMiles=1200,speedLaden=10,speedBallast=10,portDays=5,cargoTonnes=100000,freightPerTonne=20,commissionPct=5,fuelLaden=30,fuelBallast=20,fuelPort=5,fuelPrice=500,portCosts=100000,otherVoyageCosts=50000,dailyOpex=10000)
        for k,v in vals.items():page.locator('.sw56-inputs [name="'+k+'"]').fill(str(v))
        page.locator('.sw56-voyage [type=submit]').click()
        assert '76,875' in page.locator('[data-voyage-output]').inner_text()
        assert 'not observed market data' in page.locator('[data-voyage-output]').inner_text()
    def industry():
        page.goto(base+"company.html?ticker=SALM.OL")
        page.locator('#companyDrivers details').first.wait_for()
        page.locator('#companyDrivers summary').first.click()
        assert 'No connected source' in page.locator('#companyDrivers details').first.inner_text()
        page.locator('#companyDrivers summary').nth(2).click()
        page.locator('#companyDrivers details').nth(2).locator('.sw55-source').first.wait_for()
    for name,fn in [('global-search',search),('metadata-export',portal),('saved-workspaces',workspaces),('voyage-scenario',voyage),('industry-gaps',industry)]:run(name,fn)
    page.close()
try:
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width,height in VIEWPORTS:
            for theme in ("dark","light"):
                ctx=browser.new_context(viewport={"width":width,"height":height},reduced_motion="reduce",has_touch=width<768,is_mobile=width<768)
                ctx.add_init_script("localStorage.setItem('stockwatch-theme','"+theme+"')")
                page=ctx.new_page()
                page.route("**/*",lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
                errors=[];failed=[];page.on("pageerror",lambda e:errors.append(str(e)))
                page.on("response",lambda r:failed.append({"status":r.status,"path":urlparse(r.url).path}) if r.url.startswith(base) and r.status>=400 else None)
                for name in PAGES:
                    errors.clear();failed.clear()
                    case={"page":name,"width":width,"theme":theme}
                    begin=time.monotonic()
                    try:
                        suffix="?ticker=SALM.OL" if name=="company" else "?q=SALM.OL" if name=="search" else ""
                        response=page.goto(base+name+".html"+suffix,wait_until="load",timeout=30000)
                        page.wait_for_load_state("networkidle",timeout=20000)
                        case["http"]=response.status
                        case["themeActual"]=page.locator("body").get_attribute("data-theme")
                        case["geometry"]=page.evaluate("""()=>({viewport:innerWidth,scrollWidth:document.documentElement.scrollWidth,bodyHeight:document.body.scrollHeight,mainText:document.querySelector('main')?.innerText.length||0,missingAlts:[...document.images].filter(i=>!i.hasAttribute('alt')).length})""")
                        case["mobileNav"]=page.locator(".sw-mobile-nav").is_visible()
                        case["brokenLocalLinks"]=page.evaluate("""()=>[...new Set([...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')).filter(v=>v&&/^[a-z][a-z0-9-]*\\.html(?:[?#]|$)/.test(v)).map(x=>x.split(/[?#]/)[0]))]""")
                        case["brokenLocalLinks"]=[x for x in case["brokenLocalLinks"] if not (ROOT/x).is_file()]
                        case["errors"]=list(errors)
                        case["failedRequests"]=list(failed)
                        case["criticalAssets"]=[x for x in failed if x["path"].endswith((".js",".css",".svg"))]
                        case["elapsedMs"]=round((time.monotonic()-begin)*1000)
                        page.screenshot(path=str(out/f"v60-{name}-{width}-{theme}.png"),timeout=15000)
                        case["passed"]=response.ok and case["themeActual"]==theme and case["geometry"]["scrollWidth"]<=case["geometry"]["viewport"]+2 and case["geometry"]["mainText"]>0 and case["mobileNav"]==(width<=1050) and not case["errors"] and not case["criticalAssets"] and not case["brokenLocalLinks"] and not case["geometry"]["missingAlts"]
                    except Exception as e:
                        case["passed"]=False;case["exception"]=str(e)[:1500]
                    report.append(case);print(json.dumps(case),flush=True)
                ctx.close()
        check_interactions(browser)
        browser.close()
finally:
    server.shutdown()
    (out/"v60-audit.json").write_text(json.dumps({"cases":report,"interactions":interaction},indent=2))
bad=[r for r in report if not r["passed"]]+[r for r in interaction if not r["passed"]]
print(f"V60: {len(report)} page/theme/viewport cases; {len(interaction)} interactions; {len(bad)} failed",flush=True)
assert len(report)==len(PAGES)*len(VIEWPORTS)*2 and len(interaction)==5 and not bad,bad[:10]
