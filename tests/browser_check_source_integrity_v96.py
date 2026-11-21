"""V96 regression: render genuine dated scanner integrity and calendar fallback."""
import functools,http.server,json,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
WIDTHS={"mobile":390,"wide":1920}
def main():
    out=ROOT/"visual-audit"/"v96-source-integrity"
    out.mkdir(parents=True,exist_ok=True)
    server=http.server.ThreadingHTTPServer(("127.0.0.1",0),
        functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    records=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=["--no-sandbox"])
            for name in ("index","calendar"):
                for device,width in WIDTHS.items():
                    for theme in ("dark","light"):
                        page=browser.new_page(viewport={"width":width,"height":900},
                                              reduced_motion="reduce")
                        errors=[]
                        page.on("pageerror",lambda e:errors.append(str(e)))
                        page.add_init_script(f"localStorage.setItem('stockwatch-theme','{theme}')")
                        try:
                            response=page.goto(
                              f"http://127.0.0.1:{server.server_port}/{name}.html",
                              wait_until="domcontentloaded",timeout=25000)
                            assert response is not None and response.status==200
                            if name=="index":
                                status=page.locator(".sw96-source-status")
                                status.wait_for(timeout=25000)
                                summary=status.locator("summary")
                                assert summary.is_visible()
                                assert "Source freshness" in summary.inner_text()
                                assert "session-verified" in summary.inner_text() or "Session coverage unavailable" in summary.inner_text()
                                assert not status.get_attribute("open"), "Diagnostics should be collapsed by default"
                                summary.click()
                                assert status.get_attribute("open") is not None
                                text=status.inner_text()
                                assert "confirmed for completed session" in text or "Completed-session coverage unavailable" in text
                                assert "Older moves are not live alerts." in text
                                assert "Inspect source coverage" in text
                            else:
                                sync=page.locator(".sw96-calendar-sync")
                                sync.wait_for(timeout=25000)
                                assert "calendar" in sync.inner_text().lower()
                                disclosures=page.locator(".sw96-recent-filings")
                                disclosures.wait_for(timeout=15000)
                                assert "not upcoming event dates" in disclosures.inner_text()
                                assert page.locator("#eventRows tr").count()>=1
                                assert disclosures.locator("tr").count()>=2
                                assert page.locator(".sw96-recent-filings a").count()>=1
                                # Linkable issuer evidence must not create upcoming events.
                                raw=json.loads((ROOT/"data/events.json").read_text(encoding="utf-8"))
                                if not raw.get("items"):
                                    assert page.locator("#eventCount").inner_text()=="0 events"
                            assert page.evaluate(
                                "document.documentElement.scrollWidth<=innerWidth+2"),(name,device,theme)
                            assert not errors,errors
                            page.screenshot(path=str(out/f"{name}-{device}-{theme}.png"),
                                animations="disabled",full_page=False)
                            records.append({"page":name,"device":device,"theme":theme,
                                            "status":response.status,
                                            "errors":errors})
                        finally:
                            page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        (out/"audit.json").write_text(json.dumps(records,indent=2),encoding="utf-8")
    print(json.dumps({"captures":len(records),"errors":0,"output":str(out)}))
if __name__=="__main__":main()
