import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const anchors=JSON.parse(readFileSync('data/shipping-world-atlas-v118.json','utf8'));
const containers=JSON.parse(readFileSync('data/shipping-ports.json','utf8'));
const roro=JSON.parse(readFileSync('data/shipping-roro-traffic.json','utf8'));
const connectivity=JSON.parse(readFileSync('data/shipping-connectivity.json','utf8'));
const lanes=JSON.parse(readFileSync('data/shipping-usda-ocean-rates-s1.json','utf8'));
const html=readFileSync('shipping.html','utf8');
const script=readFileSync('shipping-atlas-v118.js','utf8');
const css=readFileSync('shipping-atlas-v118.css','utf8');

test('geography points are explicit approximations and never ship observations',()=>{
 assert.equal(anchors.schemaVersion,1);
 assert.equal(anchors.ports.length,40);
 assert.equal(anchors.portPointCount,40);
 assert.equal(anchors.vesselSourceStatus.observations,0);
 assert.equal(anchors.vesselSourceStatus.connected,false);
 assert.equal(anchors.countryCenters.length,20);
 assert.equal(new Set(anchors.ports.map(x=>x.id)).size,40);
 for(const x of anchors.ports){
  assert.match(x.geometryQuality,/approximate/);
  assert.equal(x.sourceKind,'geographic_reference_only');
  assert.ok(Number.isFinite(x.lon)&&Math.abs(x.lon)<=180);
  assert.ok(Number.isFinite(x.lat)&&Math.abs(x.lat)<=90);
 }
 assert.match(anchors.baseGeography,/Natural Earth/);
 assert.match(anchors.sourceDescription,/NOT a live ship position/);
});
test('only actual published country/cargo/liner/price files may supply map numeric values',()=>{
 assert.equal(containers.source.status,'ok');
 const no=containers.series.find(x=>x.countryCode==='NOR');
 assert.equal(no.value,862983);assert.equal(no.period,'2024');assert.equal(no.unit,'TEU');
 const ro=roro.series.find(x=>x.countryCode==='NO');
 assert.equal(ro.value,1161);assert.equal(ro.period,'2026-Q2');assert.equal(ro.unit,'thousand tonnes');
 const co=connectivity.series.find(x=>x.country==='Norway');
 assert.equal(co.period,'2026-09');assert.ok(co.value>0);assert.match(co.unit,/index/);
 assert.equal(lanes.rates.length,2);assert.equal(lanes.rates[0].value,72.75);
 assert.equal(lanes.unit,'USD/metric_ton');assert.equal(lanes.isExecutableQuote,false);
});
test('world atlas layers explain what observed data does not mean and do not invent AIS',()=>{
 for(const file of ['shipping-atlas-v118.css','shipping-atlas-v118.js'])assert.ok(html.includes(file));
 assert.match(html,/shipping-atlas-v118.js\?v=118a/);
 for(const k of ["ports","containers","roro","connectivity","lanes","ais"])assert.match(script,new RegExp('\\b'+k+':\\{'));
 assert.match(script,/0 verified vessel positions/);
 assert.match(script,/No permitted live AIS position source/);
 assert.match(script,/not a navigational/i);
 assert.match(script,/not live ship positions|No permitted live AIS position source|No ship is plotted/i);
 assert.match(script,/schematic/i);
 assert.match(script,/TEU/);
 assert.match(script,/LSCI/);
 assert.match(script,/Ro-Ro/);
 assert.match(script,/USD\/day/);
 assert.match(script,/USD\/tonne/);
 assert.match(script,/Date|period/);
 assert.ok(!script.includes('Math.random('));
 assert.ok(!script.includes('MOCK_VESSELS'));
 assert.ok(!script.includes('aisstream.io/v0/stream'));
 assert.ok(!script.includes('fakeDemand'));
 assert.ok(css.includes('@media(max-width:620px)'));
});
test('shipping original rate deck and navigation are preserved',()=>{
 const original=['shipping-offshore-s1.js','shipping-usda-s1.js','shipping-regional-v117t.js','shipping-offshore-econ-v117t.js'];
 for(const file of original)assert.ok(html.includes(file));
 const nav=readFileSync('secondary-markets-v114.js','utf8');
 assert.ok(nav.includes("['shippingWorldMap','Interactive world map']"));
 assert.ok(readFileSync('shipping-regional-v117t.js','utf8').includes("querySelector('#shippingWorldMap')"));
 const plan=readFileSync('docs/SHIPPING-OFFSHORE-INTELLIGENCE-PRIORITY-2026-11-22.md','utf8');
 assert.ok(plan.includes('V118 — world maritime atlas'));
});
