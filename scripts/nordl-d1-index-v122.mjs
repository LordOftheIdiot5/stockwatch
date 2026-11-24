// Private D1 binding adapter; requires migrations 0001–0003 and verified store readback.
export function privateD1Index(db){
 if(!db||typeof db.batch!=='function'||typeof db.prepare!=='function')throw Error('missing_private_db');
 return Object.freeze({async admit(p){
 const r=p.revision,t=p.receipt;
 if(t.revisionId!==r.revisionId||t.objectSha256!==p.objectSha256)throw Error('index_lineage_mismatch');
 const stmt=(sql,values)=>db.prepare(sql).bind(...values);
 const results=await db.batch([
 stmt('INSERT INTO nordl_observation_revisions VALUES (?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(revision_id) DO NOTHING',[r.revisionId,r.logicalId,r.sourceId,r.seriesId,r.entityId,r.metric,r.unit,r.periodEnd,r.value,r.publishedAt,p.objectSha256,p.objectKey]),
 stmt('INSERT INTO nordl_retrieval_receipts VALUES (?,?,?,?,?) ON CONFLICT(receipt_id) DO NOTHING',[p.receiptId,r.revisionId,t.retrievedAt,t.policyId,p.receiptKey]),
 stmt('INSERT INTO nordl_receipt_raw_lineage VALUES (?,?,?,?) ON CONFLICT(receipt_id) DO NOTHING',[p.receiptId,t.sourceReceiptId,t.rawSha256,t.rawObjectKey])
 ]);
 if(!Array.isArray(results)||results.length!==3||results.some(x=>x.success!==true))throw Error('index_batch_failed');
 }});
}
