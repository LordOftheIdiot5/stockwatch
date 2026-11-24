// N04 private archive admission planner. No network, persistence or permission grants.
import {createHash} from 'node:crypto';
import {observation} from './nordl-observation-v122.mjs';
const hash=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
export function planArchive(input,policy,asOf){
 // policy must come from the trusted operator-controlled registry, not source payload.
 if(!policy||policy.rights?.retain!=='allowed'||policy.rights?.collect!=='allowed')return {status:'blocked_retention',writes:[]};
 const o=observation(input,policy,asOf);
 const revision={schemaVersion:1,logicalId:o.logicalId,revisionId:o.revisionId,sourceId:o.sourceId,seriesId:o.seriesId,entityId:o.entityId,metric:o.metric,unit:o.unit,periodEnd:o.periodEnd,value:o.value,publishedAt:o.publishedAt,sourceUrl:o.sourceUrl};
 const objectSha256=hash(revision);
 const receipt={schemaVersion:1,revisionId:o.revisionId,objectSha256,retrievedAt:o.retrievedAt,policyId:o.policyId,publicEligible:false};
 const receiptId=hash(receipt);
 return {status:'planned_only',publicEligible:false,revision,receipt,receiptId,objectSha256,objectKey:'nordl/v1/revisions/'+objectSha256+'.json',receiptKey:'nordl/v1/receipts/'+receiptId+'.json'};
}
