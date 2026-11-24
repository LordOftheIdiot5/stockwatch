// N04d dependency-injected private persistence; no deployed bindings or permissions.
import {createHash} from 'node:crypto';
import {planArchive} from './nordl-archive-envelope-v122.mjs';
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const encode=x=>Buffer.from(JSON.stringify(x),'utf8');
async function ensureObject(store,key,bytes){
 await store.putIfAbsent(key,bytes);
 const read=await store.get(key);
 if(!read||hash(read)!==hash(bytes))throw Error('object_readback_mismatch');
}
export async function persistObservation({input,policyId,asOf,sourceReceiptId}, {registry,provenance,store,index}){
 const policy=registry.resolve(policyId,input,asOf);
 if(policy.rights.retain!=='allowed')return {status:'blocked_retention'};
 // Trusted collector-side lookup, never a source-supplied rights claim.
 const lineage=await provenance.resolve(sourceReceiptId);
 if(!lineage||lineage.sourceId!==input.sourceId||lineage.sourceUrl!==input.sourceUrl||lineage.retrievedAt!==input.retrievedAt||lineage.policyId!==policyId||lineage.retentionApproved!==true||!/^[0-9a-f]{64}$/.test(lineage.sha256)||typeof lineage.objectKey!=='string'||!lineage.objectKey)throw Error('unverified_raw_lineage');
 const raw=await store.get(lineage.objectKey);
 if(!raw||hash(raw)!==lineage.sha256)throw Error('raw_readback_mismatch');
 // Collector adapter must attest the normalized observation was derived from these exact bytes.
 if(!await provenance.verifyObservation(lineage,input,raw))throw Error('observation_lineage_mismatch');
 const p=planArchive(input,policy,asOf);
 const receipt={...p.receipt,sourceReceiptId,rawSha256:lineage.sha256,rawObjectKey:lineage.objectKey};
 const receiptBytes=encode(receipt),receiptId=hash(receiptBytes),receiptKey='nordl/v1/receipts/'+receiptId+'.json';
 await ensureObject(store,p.objectKey,encode(p.revision));
 await ensureObject(store,receiptKey,receiptBytes);
 // Atomic idempotent index admission must reject conflicts, not overwrite.
 await index.admit({revision:p.revision,objectKey:p.objectKey,objectSha256:p.objectSha256,receipt,receiptId,receiptKey});
 return {status:'indexed',revisionId:p.revision.revisionId,receiptId,publicEligible:false};
}
