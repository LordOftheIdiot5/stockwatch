"""V115: actual metadata-only commercial discovery and contact journey in browser."""
import functools
import http.server
import json
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]

def main():
 server=http.server.ThreadingHTTPServer(
  ('127.0.0.1',0),
  functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 base=f'http://127.0.0.1:{server.server_port}/'
 views=[]
 try:
  with sync_playwright() as p:
   browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
   try:
    for width in (390,1440):
     context=browser.new_context(viewport={'width':width,'height':900},
       accept_downloads=True,reduced_motion='reduce')
     try:
      page=context.new_page()
      errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
      try:
       response=page.goto(base+'data-products.html',wait_until='domcontentloaded',timeout=30000)
       assert response and response.status==200
       page.locator('#dpGrid .dp-product').first.wait_for(timeout=30000)
       assert page.locator('#dpGrid .dp-product').count()==8
       assert page.get_by_text('Not launched',exact=True).count()==1
       assert page.get_by_text('Metadata only',exact=True).count()==1
       assert page.locator('.dp-path-actions .dp-request[href^="mailto:vidar@nordl.dev"]').count()==1
       assert page.locator('.dp-path-actions a[href="https://t.me/NordlOfficial"]').count()==1
       assert page.locator('#dpGrid a.dp-contact-link[href^="mailto:vidar@nordl.dev"]').count()==8
       assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3'),(width,'overflow')
       assert not errors,(width,errors)
       # Metadata-only public catalogue: no bars, prices, API keys or records in export.
       with page.expect_download() as info:
        page.locator('#dpExport').click()
       download=info.value
       assert download.suggested_filename=='stockwatch-catalog-metadata.json'
       exported=json.loads(Path(download.path()).read_text(encoding='utf-8'))
       assert len(exported['products'])==8
       assert 'No underlying data' in exported['notice']
       assert all('records' not in p and 'history' not in p and 'apiKey' not in p
           for p in exported['products'])
       # One real catalog profile filters by terms and retains its source policy.
       page.locator('#dpQuery').fill('shipping')
       cards=page.locator('#dpGrid .dp-product')
       assert cards.count()==1,(width,cards.count())
       card=cards.first
       card.locator('details summary').click()
       assert card.locator('details').get_attribute('open') is not None
       schema=json.loads(card.locator('pre.dp-schema').inner_text())
       assert schema['datasetId']=='shipping'
       assert schema['apiAvailable'] is False
       assert schema['commercialRedistributionApproved'] is False
       assert schema['sampleRecords']==[]
       assert schema['latestObservationTime'] is None
       assert len(schema['fields'])>=1
       assert 'Source-specific' in schema['sourceRightsReview']
       href=card.locator('a.dp-contact-link').get_attribute('href')
       assert href.startswith('mailto:vidar@nordl.dev?subject=')
       assert 'shipping' in href.lower()
       with page.expect_download() as info:
        card.locator('button.dp-schema-export').click()
       schema_dl=json.loads(Path(info.value.path()).read_text(encoding='utf-8'))
       assert schema_dl==schema
       # Navigation and keyboard remain accessible with new UI.
       card.locator('a.dp-contact-link').focus()
       assert card.locator('a.dp-contact-link').evaluate('(a)=>a===document.activeElement')
       assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+3')
       assert not errors,(width,errors)
       out=ROOT/'workspace-previews';out.mkdir(exist_ok=True)
       page.locator('#dpQuery').fill('')
       page.screenshot(path=str(out/f'v115-data-products-{width}.png'),full_page=False,animations='disabled')
       views.append({'width':width,'profiles':8,'schemaDownload':True,'noRawExport':True})
      finally:page.close()
     finally:context.close()
   finally:browser.close()
 finally:server.shutdown();server.server_close()
 print(json.dumps({'v115':'pass','views':views}))

if __name__=='__main__':main()
