import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {createPolicyRegistry} from '../scripts/nordl-source-policy-v122.mjs';
import {persistObservation} from '../scripts/nordl-private-storage-v122.mjs';
const policy={policyId:'fixture',sourceId:'fixture',seriesId:'series',entityId:'entity',metric:'metric',unit:'units',sourceUrl:'https://example.com/source',evidence:'synthetic test only',rights:{collect:'allowed',retain:'allowed',display:'blocked',export:'blocked'}};
const input={...policy,value:3,periodEnd:'2026-11-01',retrievedAt:'2026-11-02T00:00:00Z'};
const request={input,policyId:'fixture',sourceReceiptId:'fixture-receipt',asOf:'2026-11-24T00:00:00Z'};
function setup(retain='allowed'){
 const raw=Buffer.from(JSON.stringify({value:3})),objects=new Map([['raw/fixture',raw]]),rows=new Map();
 const lineage={sourceId:input.sourceId,sourceUrl:input.sourceUrl,retrievedAt:input.retrievedAt,policyId:'fixture',retentionApproved:true,sha256:createHash('sha256').update(raw).digest('hex'),objectKey:'raw/fixture'};
 const deps={registry:createPolicyRegistry([{...policy,rights:{...policy.rights,retain}}]),provenance:{resolve:async id=>id==='fixture-receipt'?lineage:null,verifyObservation:async(l,i,r)=>JSON.parse(r).value===i.value},store:{get:async k=>objects.get(k),putIfAbsent:async(k,v)=>{if(!objects.has(k))objects.set(k,Buffer.from(v));}},index:{admit:async row=>rows.set(row.receiptId,row)}};
 return {deps,objects,rows,lineage};
}
test('readback before index, repeated request idempotent',async()=>{
 const {deps,objects,rows}=setup();const a=await persistObservation(request,deps),b=await persistObservation(request,deps);
 assert.deepEqual(a,b);assert.equal(objects.size,3);assert.equal(rows.size,1);
});
test('unreviewed retention blocks every write',async()=>{
 const {deps,objects,rows}=setup('unreviewed');assert.equal((await persistObservation(request,deps)).status,'blocked_retention');assert.equal(objects.size,1);assert.equal(rows.size,0);
});
test('raw corruption, forged receipt and changed value rejected',async()=>{
 const {deps,objects,rows}=setup();
 await assert.rejects(persistObservation({...request,sourceReceiptId:'fake'},deps));
 await assert.rejects(persistObservation({...request,input:{...input,value:4}},deps));
 objects.set('raw/fixture',Buffer.from('bad'));await assert.rejects(persistObservation(request,deps));assert.equal(rows.size,0);
});
test('index failure leaves recoverable immutable objects; retry succeeds',async()=>{
 const {deps,objects,rows}=setup();const admit=deps.index.admit;deps.index.admit=async()=>{throw Error('failure');};
 await assert.rejects(persistObservation(request,deps));assert.equal(objects.size,3);assert.equal(rows.size,0);
 deps.index.admit=admit;await persistObservation(request,deps);assert.equal(objects.size,3);assert.equal(rows.size,1);
});
test('corrupted normalized object never reaches index',async()=>{
 const {deps,rows}=setup();const put=deps.store.putIfAbsent;deps.store.putIfAbsent=async(k,v)=>put(k,Buffer.from('bad'));
 await assert.rejects(persistObservation(request,deps));assert.equal(rows.size,0);
});
