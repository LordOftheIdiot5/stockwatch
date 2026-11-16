import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const s=fs.readFileSync(new URL('../v4.js',import.meta.url),'utf8');
const pick=(a,b)=>s.slice(s.indexOf(a),s.indexOf(b,s.indexOf(a)));
const {alignedLicensedPair,alignedPairStats}=Function(pick('function chartSeries(','function chartWindow(')+pick('function alignedPairStats(','function pairStatsPanel(')+'\nreturn {alignedLicensedPair,alignedPairStats}')();
const h=bars=>({bars,source:'fixture',currency:'NOK',adjusted:false,redistributionPermitted:true});
test('aligned dates and source restrictions',()=>{
 const a=h([{date:'2025-01-01',close:10},{date:'2025-01-02',close:12}]),b=h([{date:'2025-01-02',close:6},{date:'2025-01-03',close:8}]);
 assert.deepEqual(alignedLicensedPair(a,b),[{date:'2025-01-02',value:2}]);
 assert.deepEqual(alignedLicensedPair(a,{...b,currency:'SEK'}),[]);
 assert.deepEqual(alignedLicensedPair(a,{...b,source:'other'}),[]);
 assert.deepEqual(alignedLicensedPair(a,{...b,redistributionPermitted:false}),[]);
});
test('no z score for insufficient data or constant series',()=>{
 assert.equal(alignedPairStats([{date:'2025-01-01',value:1.1}]).z,null);
 const a=Array.from({length:30},(_,i)=>({date:new Date(Date.UTC(2025,0,i+1)).toISOString().slice(0,10),value:1+i/100}));
 assert.ok(Number.isFinite(alignedPairStats(a).z));
 assert.equal(alignedPairStats(a.map(p=>({...p,value:1}))).z,null);
});
