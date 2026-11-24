import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {Miniflare,convertV4MiniflareOptions} from 'miniflare';
import {privateR2Store} from '../scripts/nordl-r2-store-v122.mjs';
import {privateD1Index} from '../scripts/nordl-d1-index-v122.mjs';
import {createPolicyRegistry} from '../scripts/nordl-source-policy-v122.mjs';
import {persistObservation} from '../scripts/nordl-private-storage-v122.mjs';
const hash=x=>createHash('sha256').update(x).digest('hex');
test('isolated workerd R2/D1 replay and immutable readback',async()=>{
 const mf=new Miniflare(convertV4MiniflareOptions({modules:true,script:'export default {fetch(){return new Response("Not Found",{status:404})}}',compatibilityDate:'2026-11-21',cf:false,r2Buckets:{ARCHIVE:'private-test'},d1Databases:{DB:'private-test'}}));
 try{
 const db=await mf.getD1Database('DB'),bucket=await mf.getR2Bucket('ARCHIVE');
 for(const name of ['0001_private_observations.sql','0002_raw_lineage.sql','0003_immutable_guards.sql']){
 const sql=readFileSync(new URL('../docs/nordl-schema/'+name,import.meta.url),'utf8').replace(/^--.*$/gm,'');
 const statements=name.startsWith('0003')?sql.split(/(?<=END;)/):sql.split(';');
 for(const s of statements.map(s=>s.trim()).filter(Boolean))await db.prepare(s).run();
 }
 const raw=Buffer.from('{"value":3}');await bucket.put('raw/fixture',raw);
 const policy={policyId:'fixture',sourceId:'fixture',seriesId:'series',entityId:'entity',metric:'metric',unit:'units',sourceUrl:'https://example.com/source',evidence:'synthetic test only',rights:{collect:'allowed',retain:'allowed',display:'blocked',export:'blocked'}};
 const input={...policy,value:3,periodEnd:'2026-11-01',retrievedAt:'2026-11-02T00:00:00Z'};
 const req={input,policyId:'fixture',sourceReceiptId:'fixture-receipt',asOf:'2026-11-24T00:00:00Z'};
 const lineage={sourceId:input.sourceId,sourceUrl:input.sourceUrl,retrievedAt:input.retrievedAt,policyId:'fixture',retentionApproved:true,sha256:hash(raw),objectKey:'raw/fixture'};
 const deps={registry:createPolicyRegistry([policy]),provenance:{resolve:async()=>lineage,verifyObservation:async(l,i,r)=>JSON.parse(Buffer.from(r)).value===i.value},store:privateR2Store(bucket),index:privateD1Index(db)};
 const a=await persistObservation(req,deps),b=await persistObservation(req,deps);assert.deepEqual(a,b);
 const row=await db.prepare('SELECT * FROM nordl_observation_revisions').first();
 assert.equal(row.value,3);assert.equal(hash(await deps.store.get(row.object_key)),row.object_sha256);
 assert.equal((await db.prepare('SELECT count(*) AS n FROM nordl_retrieval_receipts').first()).n,1);
 assert.equal((await db.prepare('SELECT count(*) AS n FROM nordl_receipt_raw_lineage').first()).n,1);
 await deps.store.putIfAbsent(row.object_key,Buffer.from('overwrite attempt'));
 assert.equal(hash(await deps.store.get(row.object_key)),row.object_sha256);
 assert.equal((await mf.dispatchFetch('http://localhost/private')).status,404);
 }finally{await mf.dispose();}
});
