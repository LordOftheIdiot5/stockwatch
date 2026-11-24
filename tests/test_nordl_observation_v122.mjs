import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {shippingPilot} from '../scripts/nordl-shipping-pilot-v122.mjs';
import {observation,weeklyChange} from '../scripts/nordl-observation-v122.mjs';
const data=JSON.parse(readFileSync(new URL('../data/shipping-open.json',import.meta.url)));
const asOf=data.generated;
test('actual stored USDA data yields comparable private observations',()=>{
 const p=shippingPilot(data,asOf);assert.equal(p.results.length,2);assert.equal(p.missing.length,0);
 for(const x of p.results){assert.equal(x.signal.publicEligible,false);assert.equal(x.current.publishedAt,null);assert.equal(x.current.rights.export,'unreviewed');assert.equal(x.signal.changePct,(x.current.value/x.previous.value-1)*100);}
});
test('wrong unit, wrong source, duplicates and missing dates fail closed',()=>{
 for(const mutate of [s=>s.unit='USD/t',s=>s.sourceUrl='https://example.com/x',s=>s.history.push(s.history.at(-1)),s=>s.history.at(-2).date='2000-01-01']){
 const d=structuredClone(data);mutate(d.series[0]);assert.equal(shippingPilot(d,asOf).results.length,1);
 }
});
test('future vintage and stale records rejected',()=>{
 assert.equal(shippingPilot(data,'2000-01-01T00:00:00Z').results.length,0);
 assert.equal(shippingPilot(data,'2099-01-01T00:00:00Z').results.length,0);
});
test('different identities and periods cannot be compared',()=>{
 const {current,previous}=shippingPilot(data,asOf).results[0];
 assert.equal(weeklyChange(current,{...previous,entityId:'other'}),null);
 assert.equal(weeklyChange(current,{...previous,periodEnd:current.periodEnd}),null);
});
test('missing policy cannot authorize collection',()=>assert.throws(()=>observation({},null,asOf)));
