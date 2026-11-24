// N03: private candidate contract; no publication or storage entitlement inferred.
import {createHash} from 'node:crypto';
const digest=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x;
const stamp=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/.test(x)&&day(x.slice(0,10))&&Number.isFinite(Date.parse(x));
const nonempty=x=>typeof x==='string'&&x.trim()===x&&x.length>0&&x.length<=500;
const rightsKeys=['collect','retain','display','export'];
export function observation(input,policy,asOf){
 if(!stamp(asOf)||!input||!policy)throw Error('invalid_context');
 const {sourceId,seriesId,entityId,metric,unit,periodEnd,value,retrievedAt,publishedAt=null}=input;
 if(![sourceId,seriesId,entityId,metric,unit].every(nonempty)||!day(periodEnd)||!stamp(retrievedAt)||typeof value!=='number'||!Number.isFinite(value))throw Error('invalid_observation');
 if(Date.parse(retrievedAt)>Date.parse(asOf)||periodEnd>retrievedAt.slice(0,10)||publishedAt!==null&&(!stamp(publishedAt)||Date.parse(publishedAt)>Date.parse(retrievedAt)))throw Error('future_or_invalid_vintage');
 if(policy.sourceId!==sourceId||policy.seriesId!==seriesId||policy.entityId!==entityId||policy.metric!==metric||policy.unit!==unit||policy.sourceUrl!==input.sourceUrl||!nonempty(policy.policyId)||!nonempty(policy.evidence)||!rightsKeys.every(k=>['allowed','blocked','unreviewed'].includes(policy.rights?.[k]))||policy.rights.collect!=='allowed')throw Error('source_policy_mismatch');
 const url=new URL(policy.sourceUrl);if(url.protocol!=='https:'||url.username||url.password)throw Error('invalid_source_url');
 const logicalId=digest([sourceId,seriesId,entityId,metric,unit,periodEnd]);
 const revisionId=digest([logicalId,value,publishedAt]);
 return Object.freeze({schemaVersion:1,logicalId,revisionId,sourceId,seriesId,entityId,metric,unit,periodEnd,value,retrievedAt,publishedAt,sourceUrl:policy.sourceUrl,policyId:policy.policyId,rights:Object.freeze(Object.fromEntries(rightsKeys.map(k=>[k,policy.rights[k]])))});
}
export function weeklyChange(current,previous){
 if(!current||!previous||!['sourceId','seriesId','entityId','metric','unit','sourceUrl','policyId'].every(k=>current[k]===previous[k])||Date.parse(current.periodEnd)-Date.parse(previous.periodEnd)!==604800000||previous.value<=0||current.value<0)return null;
 const changePct=(current.value/previous.value-1)*100;
 if(!Number.isFinite(changePct))return null;
 return {schemaVersion:1,algorithm:'weekly-change-v1',kind:'observed_comparison',inputRevisionIds:[current.revisionId,previous.revisionId],currentPeriod:current.periodEnd,baselinePeriod:previous.periodEnd,unit:current.unit,value:current.value,baseline:previous.value,changePct,publicEligible:false};
}
