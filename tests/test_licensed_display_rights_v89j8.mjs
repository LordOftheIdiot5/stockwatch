'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'../v4.js'),'utf8');
const begin=src.indexOf('function licensedReferenceRows('),end=src.indexOf('function licensedReferenceCount(',begin);
assert.ok(begin>=0&&end>begin);
const rows=Function(src.slice(begin,end)+'\nreturn licensedReferenceRows')();
const native=require('../native-chart.js');
const listingId='ref:XOSL:EQNR';
const sample={listingId,priceType:'end_of_day',publicDisplayPermitted:true,redistributionPermitted:false,rawRedistributionPermitted:false,historyPath:'data/licensed-reference-history/'+'a'.repeat(32)+'.json',close:102,changePct:2,lastDate:'2026-11-19',currency:'NOK',source:'Licensed example',sourceUrl:'https://example.invalid/source',licenseReference:'https://example.invalid/license',adjusted:false};
const universe=[{ticker:listingId,referenceOnly:true},{ticker:'EQNR.OL',referenceOnly:false}];
test('display-only licensed EOD is recognized in directory and price history',()=>{
 assert.equal(rows({records:[sample]},universe).get(listingId).close,102);
 assert.equal(native.authorized(sample,sample),true);
});
test('explicit display denial cannot be bypassed by a raw redistribution flag',()=>{
 const q={...sample,publicDisplayPermitted:false,redistributionPermitted:true};
 assert.equal(rows({records:[q]},universe).has(listingId),false);
 assert.equal(native.authorized(q,q),false);
});
test('legacy fully authorized records retain backward compatibility',()=>{
 const q={...sample};delete q.publicDisplayPermitted;q.redistributionPermitted=true;
 assert.equal(rows({records:[q]},universe).has(listingId),true);
 assert.equal(native.authorized(q,q),true);
});
test('missing display permission is denied',()=>{
 const q={...sample};delete q.publicDisplayPermitted;q.redistributionPermitted=false;
 assert.equal(rows({records:[q]},universe).has(listingId),false);
 assert.equal(native.authorized(q,q),false);
});
