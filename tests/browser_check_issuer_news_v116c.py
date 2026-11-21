"""V116c: ensure the financial news rail never promotes unverified acronym matches.

Use the checked-in source's exact issuer-code/source-issuer/relevance flags:
news headlines with the same company acronym are research candidates, not
confirmed issuer disclosures. Preserve the archive for review.
"""
import functools
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def main():
    archive=json.loads((ROOT/'data/news-latest.json').read_text(encoding='utf-8'))
    items=archive.get('items', [])
    verified=[
        x for x in items if x.get('match')=='issuer_code'
        and x.get('relevance')=='strong' and x.get('sourceIssuer')
        and x.get('regulatory') is True
    ]
    allowed=set()
    for row in verified:
        allowed.add(row.get('headline','').strip())
        if row.get('english'):allowed.add(row['english'].strip())

    server=http.server.ThreadingHTTPServer(
       ('127.0.0.1',0),
       functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    results=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                for width in (390,1440,1920):
                    page=browser.new_page(viewport={'width':width,'height':941},
                     reduced_motion='reduce')
                    errors=[]
                    page.on('pageerror',lambda e:errors.append(str(e)))
                    try:
                        resp=page.goto(f'http://127.0.0.1:{server.server_port}/index.html',
                         wait_until='domcontentloaded',timeout=30000)
                        page.locator('.sw-overview-news').wait_for(timeout=30000)
                        page.locator('.sw-overview-news .sw-panel-hd').wait_for(timeout=30000)
                        rail=page.locator('.sw-overview-news')
                        assert 'Verified issuer disclosures' in rail.inner_text()
                        titles=rail.locator('.sw-brief h4').all_inner_texts()
                        assert len(titles)<=4,(width,titles)
                        assert all(x.strip() in allowed for x in titles),(width,titles,allowed)
                        if not verified:
                            assert 'No issuer-verified disclosures' in rail.inner_text()
                        assert 'CAF launches U-17' not in rail.inner_text()
                        assert 'Andrew Kamanga' not in rail.inner_text()
                        assert 'Ferrari Challenge' not in page.locator('#overviewEvents').inner_text()
                        assert resp and resp.status==200
                        assert not errors,errors
                        results.append({'width':width,'verified_available':len(verified),
                         'rendered_disclosures':len(titles),'titles':titles})
                    finally:page.close()
            finally:browser.close()
    finally:server.shutdown();server.server_close()
    print(json.dumps({'v116c':'issuer-news-verified','cases':results},indent=2))
    assert len(results)==3

if __name__=='__main__':
    main()
