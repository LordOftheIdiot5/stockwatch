"""V105: Data Health daily coverage rendering on real 500-listing snapshot, desktop/mobile."""
from __future__ import annotations

import functools
import http.server
import json
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0),
        functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    )
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True, args=["--no-sandbox"])
            for width in (390, 1440):
                page = browser.new_page(viewport={"width": width, "height": 900})
                errors = []
                page.on("pageerror", lambda err: errors.append(str(err)))
                page.goto(f"http://127.0.0.1:{server.server_port}/health.html",
                          wait_until="domcontentloaded", timeout=30000)
                root = page.locator("#dailyPriceCoverage")
                root.locator(".sw105-table tbody tr").first.wait_for(timeout=25000)
                assert root.locator(".sw105-stat").count() == 6
                assert "Research listings" in root.inner_text()
                assert "Still without a price" in root.inner_text()
                assert "Monitored session comparable" in root.inner_text()
                assert root.locator(".sw105-table tbody tr").count() >= 10
                assert page.locator("#marketCoverage").count() == 1
                assert page.locator("#venuePriceEvidence").count() == 1
                assert page.locator('a[href="data/daily-price-recovery-v105.json"]').count() == 1
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
                assert not errors, errors
                output = ROOT / "workspace-previews"
                output.mkdir(exist_ok=True)
                page.screenshot(path=str(output/f"v105-daily-coverage-{width}.png"),
                                animations="disabled")
                results.append({"width": width, "venueRows": root.locator(".sw105-table tbody tr").count(),
                                "errors": errors})
                page.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print(json.dumps({"result": "passed", "devices": results}))


if __name__ == "__main__":
    main()
