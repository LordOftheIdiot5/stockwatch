'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {build}=require('../scripts/listing_enrichment_queue.cjs');
const a={id:'A.OL',name:'A',venue:'Oslo',group:'monitored',mic:'XOSL',isin:'NO0010096985',identityStatus:'isin_and_mic',priceStatus:'scanner',priceDate:'2026-11-19',newsRecords:1,sector:'Energy',licensedHistory:false};
const b={id:'registry:XSTO:ABC',name:'B',venue:'Stockholm',group:'registry',mic:'XSTO',figi:'BBG000000000',identityStatus:'figi_and_mic',priceStatus:'missing'};
const inventory=records=>({summary:{listings:records.length},generated:'2026-11-20T00:00:00Z',records});
test('one row per current or newly added listing',()=>{const q=build(inventory([a,b]));assert.equal(q.listings,2);assert.equal(q.records[1].priceRoute,'nasdaq_nordic');assert.equal(q.records[1].tasks.price,'await_identity');assert.equal(q.records[1].tasks.news,'match_issuer_and_collect');assert.equal(q.records[0].tasks.price,'dated_observation_present');assert.equal(q.records[0].tasks.historical_prices,'review_retention_and_collect');assert.equal(q.totals.price.await_identity,1)});
test('exact identity is not a licence',()=>{const q=build(inventory([{...a,priceStatus:'missing',priceDate:null}]));assert.equal(q.records[0].tasks.price,'review_authorized_price_route');assert.equal(q.records[0].priceDate,null)});
test('reject duplicate IDs and wrong denominator',()=>{assert.throws(()=>build(inventory([a,a])));assert.throws(()=>build({...inventory([a]),summary:{listings:2}}))});
