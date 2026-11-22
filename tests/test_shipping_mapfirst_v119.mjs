import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const html=fs.readFileSync('shipping.html','utf8');
const js=fs.readFileSync('shipping-mapfirst-v119.js','utf8');
const css=fs.readFileSync('shipping-mapfirst-v119.css','utf8');
const borders=JSON.parse(fs.readFileSync('data/shipping-world-borders-v119.json','utf8'));
const atlas=fs.readFileSync('shipping-atlas-v118.js','utf8');
const geography=JSON.parse(fs.readFileSync('data/shipping-world-atlas-v118.json','utf8'));
const data=JSON.parse(fs.readFileSync('data/shipping-ports.json','utf8'));

test('V119 is a full-viewport source-backed atlas, not a discarded shipping library',()=>{
 assert.match(html,/shipping-mapfirst-v119\.css\?v=119a/);
 assert.match(html,/shipping-mapfirst-v119\.js\?v=119a/);
 for(const p of ['v4.js','shipping-offshore-s1.js','shipping-usda-s1.js','shipping-regional-v117t.js','shipping-offshore-econ-v117t.js','shipping-atlas-v118.js'])assert.ok(html.includes(p),p);
 assert.match(js,/app\.prepend\(atlas\)/);
 assert.match(js,/insertAdjacentElement\('afterend',details\)/);
 assert.match(js,/sw119-research-intro/);
 for(const s of ['#offshoreRates','#usdaRouteRates','#nordicMaritime','#worldBankPortTraffic','#roroMarketTraffic','#unctadConnectivity','#routeCompare','#shippingBenchmarkAnchor','#navprofitEconomics','#voyageEstimator','#shippingDataGuide'])assert.ok(js.includes(s),s);
 assert.match(css,/#v4app>#shippingWorldMap/);
 assert.match(css,/100dvh/);
 assert.match(css,/\.sw119-topbar/);
 assert.match(css,/\.sw119-research-shortcuts/);
});
test('Natural Earth boundary layer is public domain, reused from Energy, and not routes or ship positions',()=>{
 assert.equal(borders.type,'FeatureCollection');
 assert.equal(borders.license,'Public domain');
 assert.ok(borders.features.length>=250);
 assert.match(borders.source,/natural-earth-vector/);
 assert.equal(geography.vesselSourceStatus.connected,false);
 assert.equal(geography.vesselSourceStatus.observations,0);
 assert.equal(geography.ports.length,40);
 assert.ok(js.includes('data/shipping-world-borders-v119.json'));
 assert.ok(js.includes("d.license!=='Public domain'"));
 assert.match(js,/no live AIS|does not.*vessel|does not.*ship|never/i);
 assert.ok(!js.includes('Math.random('));
 assert.ok(!js.includes('MOCK_SHIPS'));
 assert.ok(!js.includes('aisstream.io'));
 assert.ok(!js.includes('localStorage'));
});
test('selected-port country totals are never attributed to individual terminals',()=>{
 const n=data.series.find(x=>x.countryCode==='NLD');
 assert.ok(n);
 assert.equal(n.value,14517179);
 assert.equal(n.period,'2024');
 assert.equal(n.unit,'TEU');
 assert.match(js,/NOT the selected port alone or current shipping demand/);
 assert.match(js,/country container handling/i);
 assert.match(js,/World Bank unavailable/);
 assert.match(js,/Original/ig); // explicit original-market context
 assert.match(atlas,/No live AIS feed connected/);
});
test('map navigation is keyboard accessible, protected on mobile and keeps the research menu',()=>{
 assert.match(js,/sw119-inspector-close/);
 assert.match(js,/aria-label','Close map details/);
 assert.match(js,/sw119-research-menu/);
 assert.match(js,/sw119-back-map/);
 assert.match(css,/@media\(max-width:900px\)/);
 assert.match(css,/@media\(max-width:540px\)/);
 assert.match(css,/focus-visible/);
 assert.match(css,/\.sw119-inspector-open/);
});
