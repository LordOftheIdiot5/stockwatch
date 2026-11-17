import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),N=require('../company-network-v84.js');
const load=p=>JSON.parse(fs.readFileSync(new URL('../data/'+p,import.meta.url),'utf8'));
test('V84 evidence graph preserves exact directions and amount bases',()=>{
 const data=load('company-relationships.json'),g=N.graph(data);
 assert.equal(g.nodes.size,40);assert.equal(g.edges.length,34);
 const n=N.neighborhood(g,'spacex');
 assert.equal(n.edges.length,2);
 assert.ok(n.edges.some(e=>e.from==='singulus'&&e.to==='spacex'&&e.type==='supply_contract'&&N.amountLabel(e.amount).startsWith('> EUR 60 m')));
 assert.ok(n.edges.some(e=>e.from==='spacex'&&e.to==='singulus'&&e.type==='financing'));
 assert.equal(N.neighborhood(g,'spacex','all',2).edges.length,3);
 assert.equal(N.neighborhood(g,'spacex','financing').edges.length,1);
 assert.equal(N.entityForListing(data,'XNAS:NVDA'),'nvidia');
 assert.equal(N.entityForListing(data,'ref:XNAS:NVDA'),'nvidia');
 assert.equal(N.entityForListing(data,null),null);
 assert.equal(N.amountLabel(null),'Amount not disclosed');
});
test('V84 never displays review-only, fake cash-flow or malformed evidence',()=>{
 const data=load('company-relationships.json');
 for(const change of [{actualCashFlow:true},{evidenceStatus:'review_required'},{sourceUrl:'javascript:alert(1)'},{amount:{value:0,currency:'USD',comparison:'exact_reported',basis:'unknown'}},{disclosedOn:'2026-12-31'}]){
  const clone=structuredClone(data);clone.relationships[0]={...clone.relationships[0],...change};assert.equal(N.graph(clone).edges.length,33);
 }
});
test('V84 local photo attribution and exact listing matching',()=>{
 const d=load('company-image-catalog.json');
 for(const a of d.assets){
  assert.equal(a.status,'imported');assert.ok(fs.existsSync(new URL('../'+a.localAsset,import.meta.url)));
  const html=N.photo(d,a.listing);assert.ok(html.includes(a.localAsset));assert.ok(html.includes(a.license));assert.ok(html.includes('Original photograph'));
 }
 assert.equal(N.photo(d,'unknown'),'');
 const bad=structuredClone(d);bad.assets[0].localAsset='https://example.com/photo.webp';assert.equal(N.photo(bad,bad.assets[0].listing),'');
});
test('US cohort exposes only exact reference identifiers, no quotes',()=>{
 const data=load('us-equity-seed.json');
 assert.equal(data.records.length,50);assert.equal(new Set(data.records.map(r=>r.id)).size,50);
 assert.ok(data.records.every(r=>/^\d{10}$/.test(r.cik)&&r.quoteStatus==='not_connected'&&r.currency==='USD'));
});

test('Expanded contracts preserve upper bounds and prevent syndicate double counting',()=>{
 const data=load('company-relationships.json'),g=N.graph(data);
 const aggregate=g.edges.find(e=>e.id==='coreweave-openai-aggregate');
 assert.ok(N.amountLabel(aggregate.amount).startsWith('Up to USD 22.4 bn'));
 assert.equal(aggregate.history.length,2);
 const financing=N.neighborhood(g,'premier-energy','all',2);
 const measured=financing.edges.filter(e=>e.amount!==null);
 assert.equal(measured.length,1);
 assert.equal(measured[0].amount.value,850000000);
 assert.equal(financing.edges.filter(e=>e.type==='arrangement').length,2);
 assert.equal(N.entityForListing(data,'AIR.PA'),'airbus');
});

test('News evidence preserves supplier ranges and avoids premature acquisition completion',()=>{const g=N.graph(load('company-relationships.json'));const dof=g.edges.find(e=>e.id==='dof-amplitude-surf');assert.ok(N.amountLabel(dof.amount).startsWith('USD 50–100 m'));assert.equal(g.edges.find(e=>e.id==='siemens-breker-acquisition').status,'signed_pending_close');assert.equal(N.neighborhood(g,'hoegh').edges.length,6);assert.equal(N.entityForListing(load('company-relationships.json'),'HAUTO.OL'),'hoegh');const bad=load('company-relationships.json');bad.relationships.find(e=>e.id==='dof-amplitude-surf').amount.upperValue=1;assert.equal(N.graph(bad).edges.length,33);});
