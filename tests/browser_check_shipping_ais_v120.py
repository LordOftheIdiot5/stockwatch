"""V120c gated AIS browser acceptance: no synthetic production ships."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import functools
import http.server
import json
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
ENDPOINT='https://stockwatch-marine-ais.v120-tests.workers.dev/api/marine/vessels'

def snapshot(stale=False):
    now=int(time.time()*1000)
    position=now-(31 if stale else 1)*60000
    return {'schemaVersion':1,'sourceId':'fintraffic-ais-v1',
            'provider':'Fintraffic Digitraffic','license':'CC BY 4.0',
            'sourceUrl':'https://meri.digitraffic.fi/api/ais/v1/locations',
            'retrievedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(now/1000)),
            'positions':[{'mmsi':230949000,'imo':8325121,'name':'HELGA',
                          'vesselClass':'Cargo','destinationAisReported':'SAVONLINNA',
                          'longitude':28.927335,'latitude':61.856277,
                          'speedKnots':11.2,'courseDegrees':189.5,'headingDegrees':190,
                          'metadataReportedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime((now-120000)/1000)),
                          'positionReportedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(position/1000))}],
            'positionCount':1,'coverage':'Fintraffic Finnish AIS receiver network only'}
def mock_config(route):
    route.fulfill(status=200,content_type='application/json',body=json.dumps({
        'schemaVersion':1,'enabled':True,'endpoint':ENDPOINT,
        'sourceId':'fintraffic-ais-v1'}))
def main():
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),
        functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    outcomes=[]
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True,args=['--no-sandbox'])
            try:
                base='http://127.0.0.1:'+str(server.server_port)+'/shipping.html'
                # Default production gate: zero positions, no upstream request.
                p=browser.new_page(viewport={'width':390,'height':860})
                requests=[]
                p.on('request',lambda r: requests.append(r.url) if 'api/marine/vessels' in r.url else None)
                p.goto(base,wait_until='domcontentloaded')
                p.locator('#shippingMapPins .sw-atlas-point').first.wait_for(timeout=30000)
                p.locator('[data-layer="ais"]').click()
                assert '0 verified vessel positions' in p.locator('#shippingMapCount').inner_text()
                assert p.locator('#shippingMapPins .sw-atlas-vessel').count()==0
                p.wait_for_timeout(200)
                assert requests==[]
                assert 'No live AIS feed connected' in p.locator('#shippingMapDetailTitle').inner_text()
                p.close()
                outcomes.append('default_off=PASS')
                # Fixture is strictly an intercepted test reply, never a public dataset.
                for width in (390,1440):
                    p=browser.new_page(viewport={'width':width,'height':940},reduced_motion='reduce')
                    errors=[]
                    p.on('pageerror',lambda e:errors.append(str(e)))
                    p.route('**/data/shipping-ais-v120-config.json',mock_config)
                    p.route(ENDPOINT,lambda route:route.fulfill(status=200,content_type='application/json',headers={'access-control-allow-origin':'*'},body=json.dumps(snapshot())))
                    p.goto(base,wait_until='domcontentloaded')
                    p.locator('#shippingMapPins .sw-atlas-point').first.wait_for(timeout=30000)
                    p.locator('[data-layer="ais"]').click()
                    p.locator('#shippingMapPins .sw-atlas-vessel').first.wait_for(timeout=12000)
                    assert p.locator('#shippingMapPins .sw-atlas-vessel').count()==1
                    assert '1 timestamped vessel positions' in p.locator('#shippingMapCount').inner_text()
                    assert 'Fintraffic' in p.locator('#shippingMapLegend').text_content()
                    p.locator('#shippingMapPick').select_option('vessel:230949000')
                    assert 'HELGA' in p.locator('#shippingMapDetailTitle').inner_text()
                    facts=p.locator('#shippingMapFact').inner_text()
                    assert '11.2 kn' in facts and 'SAVONLINNA' in facts
                    assert 'AIS position reported' in facts
                    assert 'Fintraffic' in p.locator('#shippingMapSourceStatus').inner_text()
                    assert p.evaluate('document.documentElement.scrollWidth<=innerWidth+3'),width
                    assert not errors,(width,errors)
                    p.close()
                    outcomes.append(str(width)+'px_verified_fixture=PASS')
                # An old source point is not drawn even when the mock endpoint returns 200.
                p=browser.new_page(viewport={'width':390,'height':860})
                p.route('**/data/shipping-ais-v120-config.json',mock_config)
                p.route(ENDPOINT,lambda route:route.fulfill(status=200,content_type='application/json',headers={'access-control-allow-origin':'*'},body=json.dumps(snapshot(stale=True))))
                p.goto(base,wait_until='domcontentloaded')
                p.locator('#shippingMapPins .sw-atlas-point').first.wait_for(timeout=30000)
                p.locator('[data-layer="ais"]').click()
                p.get_by_text('AIS feed unavailable or stale',exact=False).first.wait_for(timeout=10000)
                assert p.locator('#shippingMapPins .sw-atlas-vessel').count()==0
                p.close()
                outcomes.append('stale_rejected=PASS')
            finally:browser.close()
    finally:server.shutdown();server.server_close()
    print(json.dumps({'result':'PASS','checks':outcomes}))
if __name__=='__main__':main()
