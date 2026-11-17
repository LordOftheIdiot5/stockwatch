import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {cleanBars,authorized}=require('../native-chart.js');
const {chartWindow,navigateChart}=require('../research-analytics.js');
test('preserve genuine OHLC and do not synthesize missing candles',()=>{
const [a,b]=cleanBars([{date:'2026-01-02',close:10,open:9,high:12,low:8,volume:42},{date:'2026-01-03',close:11,open:10,high:9,low:8}]);
assert.equal(a.high,12);assert.equal(a.volume,42);assert.equal(b.open,undefined);assert.equal(b.close,11);
});
test('reject conflicting duplicate dates and invalid bars',()=>{
assert.deepEqual(cleanBars([{date:'2026-02-30',close:3},{date:'2026-01-01',close:2},{date:'2026-01-01',close:3}]),[]);
});
test('authorization matches listing source currency and entitlement',()=>{
const e={listingId:'TEST',currency:'NOK',source:'test',licenseReference:'https://example.com/licence',redistributionPermitted:true,priceType:'end_of_day',historyPath:'data/licensed-reference-history/'+'a'.repeat(32)+'.json',adjusted:false};
const h={...e,sourceUrl:'https://example.com/source'};
assert.equal(authorized(e,h),true);assert.equal(authorized(e,{...h,redistributionPermitted:false}),false);assert.equal(authorized(e,{...h,adjusted:true}),false);assert.equal(authorized(e,{...h,currency:'USD'}),false);
});
test('chart navigation is bounded',()=>{let r=chartWindow(100,0,100);r=navigateChart(100,r,'in',50);assert.ok(r.end-r.start<100);assert.ok(r.start>=0&&r.end<=100);assert.deepEqual(navigateChart(100,r,'reset'),{start:0,end:100});});
