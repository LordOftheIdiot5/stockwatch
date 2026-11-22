import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const evidence=JSON.parse(fs.readFileSync('data/offshore-rate-evidence-v117s.json','utf8'));
const site=fs.readFileSync('shipping.html','utf8');
const module=fs.readFileSync('shipping-offshore-s1.js','utf8');
const styles=fs.readFileSync('shipping-offshore-s1.css','utf8');

test('source documents and historical rate facts are explicit',()=>{
 assert.equal(evidence.schemaVersion,1);
 assert.equal(evidence.brokerSpotRatesLicensed,0);
 assert.equal(evidence.brokerSpotRateSeries,0);
 assert.equal(evidence.sources.length,3);
 assert.equal(evidence.observations.length,18);
 assert.equal(new Set(evidence.observations.map(x=>x.id)).size,evidence.observations.length);
 const s=new Map(evidence.sources.map(x=>[x.id,x]));
 for(const x of evidence.observations){
  assert.ok(s.has(x.sourceId));assert.ok(s.get(x.sourceId).url.startsWith('https://'));
  assert.equal(x.unit,'USD/day');assert.equal(x.isBrokerSpotQuote,false);
  assert.equal(x.rateType,'issuer_reported_quarterly_average');assert.ok(x.value>0);
  assert.ok(/2026-Q[23]/.test(x.period));assert.ok(x.periodEnd&&x.rateBasis);
  assert.equal(x.sourceFactStatus,'original_issuer_disclosed');
 }
});
test('original source-linked Q3 facts match distinct issuer categories',()=>{
 const get=(src,cls,period='2026-Q3')=>evidence.observations.find(x=>x.sourceId===src&&x.vesselClass===cls&&x.period===period)?.value;
 assert.equal(get('tdw2026q3','PSV >900 m²'),34153);
 assert.equal(get('tdw2026q3','PSV <900 m²'),27875);
 assert.equal(get('tdw2026q3','AHTS >16K BHP'),35392);
 assert.equal(get('tdw2026q3','AHTS 8–16K BHP'),15211);
 assert.equal(get('tdw2026q3','AHTS 4–8K BHP'),23014);
 assert.equal(get('smhi2026q3','PSV fleet'),28052);
 assert.equal(get('smhi2026q3','Fast support vessel'),14567);
 assert.equal(get('smhi2026q3','Liftboat fleet'),26855);
 assert.equal(get('noble2026q3','Floating rigs'),403113);
 assert.equal(get('noble2026q3','Jack-up rigs'),207651);
 assert.equal(get('noble2026q3','Floating rigs','2026-Q2'),412650);
 assert.equal(get('tdw2026q3','PSV >900 m²','2026-Q2'),35554);
});
test('the site contains a real source-backed rate desk, distinct from broker rate and original freight routes',()=>{
 assert.ok(site.includes('shipping-offshore-s1.css?v=s1a'));
 assert.ok(site.includes('shipping-offshore-s1.js?v=s1a'));
 assert.ok(site.includes('Shipping &amp; offshore markets'));
 assert.ok(module.includes('data/offshore-rate-evidence-v117s.json'));
 assert.ok(module.includes('brokerSpotRatesLicensed!==0'));
 assert.ok(module.includes('issuer_reported_quarterly_average'));
 assert.ok(module.includes('Licensed daily PSV, AHTS and freight spot quotes: 0.'));
 assert.ok(module.includes('Original source ↗'));
 assert.ok(module.includes('offshoreSegment')&&module.includes('offshoreIssuer'));
 assert.ok(site.includes('secondary-markets-v114.js'));
 assert.ok(styles.includes('@media(max-width:540px)'));
 assert.ok(!module.includes('Math.random('));
});
test('same-class quarter comparisons use the same issuer and region, not different markets',()=>{
 const q3=evidence.observations.filter(x=>x.period==='2026-Q3');
 assert.equal(q3.length,11);
 const byPair=new Map(evidence.observations.map(x=>[[x.sourceId,x.vesselClass,x.region,x.period].join('|'),x]));
 const comparisons=q3.filter(x=>byPair.has([x.sourceId,x.vesselClass,x.region,'2026-Q2'].join('|')));
 assert.equal(comparisons.length,7);
 assert.ok(!comparisons.find(x=>x.sourceId==='smhi2026q3'));
 assert.ok(comparisons.every(x=>byPair.get([x.sourceId,x.vesselClass,x.region,'2026-Q2'].join('|')).unit===x.unit));
});
