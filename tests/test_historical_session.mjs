import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
const js=fs.readFileSync(new URL('../v4.js',import.meta.url),'utf8');
const a=js.indexOf('function observationQuality('),z=js.indexOf('function qualityLabel(',a),b=js.indexOf('function latestBroadSession('),e=js.indexOf('function overview()',b);
const {latestBroadSession}=Function(js.slice(a,z)+js.slice(b,e)+'\nreturn {latestBroadSession}')();
test('historical view never mixes dates or zero-volume rows',()=>{
 const row=(i,date,changePct,volume=1)=>({ticker:'X'+i,date,changePct,close:10,volume});
 const d='2026-11-13',target='2026-11-16',rows=[...Array.from({length:12},(_,i)=>row(i,d,i-6)),row(13,target,999),row(14,'2026-11-12',999),row(15,d,200,0),row(16,'2026-11-31',100)];
 const x=latestBroadSession(rows,target);assert.equal(x.day,d);assert.equal(x.rows.length,12);assert.equal(x.median,-.5);assert.equal(x.up,5);assert.equal(x.down,6);assert.equal(x.flat,1);assert.equal(latestBroadSession(rows,target,13),null);
});
