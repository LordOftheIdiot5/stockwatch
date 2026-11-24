import test from 'node:test';
import assert from 'node:assert/strict';
import {privateD1Index} from '../scripts/nordl-d1-index-v122.mjs';
const p={revision:{revisionId:'r',logicalId:'l',sourceId:'s',seriesId:'series',entityId:'e',metric:'m',unit:'u',periodEnd:'2026-11-01',value:10,publishedAt:null},objectSha256:'hash',objectKey:'object',receiptId:'receipt',receiptKey:'receipt-object',receipt:{revisionId:'r',objectSha256:'hash',retrievedAt:'2026-11-02T00:00:00Z',policyId:'policy',sourceReceiptId:'source-receipt',rawSha256:'raw-hash',rawObjectKey:'raw-object'}};
test('three bound statements use one atomic batch',async()=>{
 let batch;
 const db={prepare:sql=>({bind:(...values)=>({sql,values})}),batch:async x=>{batch=x;return x.map(()=>({success:true}));}};
 await privateD1Index(db).admit(p);
 assert.deepEqual(batch.map(x=>x.values.length),[12,5,4]);
 assert.ok(batch.every(x=>x.sql.includes('ON CONFLICT')));
 assert.equal(batch[2].values[1],'source-receipt');
});
test('mismatched lineage and failed batch rejected',async()=>{
 let calls=0;
 const db={prepare:sql=>({bind:(...values)=>({sql,values})}),batch:async()=>{calls++;return [{success:false}];}};
 await assert.rejects(privateD1Index(db).admit({...p,receipt:{...p.receipt,revisionId:'other'}}));
 assert.equal(calls,0);
 await assert.rejects(privateD1Index(db).admit(p));
 assert.equal(calls,1);
});
