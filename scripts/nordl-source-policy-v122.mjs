// N04b: registry boundary. No real retention permission is granted here.
import {observation} from './nordl-observation-v122.mjs';
const keys=['collect','retain','display','export'];
export function createPolicyRegistry(entries){
 if(!Array.isArray(entries))throw Error('invalid_registry');
 const map=new Map();
 for(const entry of entries){
 if(!entry||typeof entry.policyId!=='string'||!entry.policyId.trim()||map.has(entry.policyId)||typeof entry.evidence!=='string'||!entry.evidence.trim()||!keys.every(k=>['allowed','blocked','unreviewed'].includes(entry.rights?.[k])))throw Error('invalid_policy');
 for(const k of ['sourceId','seriesId','entityId','metric','unit','sourceUrl'])if(typeof entry[k]!=='string'||!entry[k].trim())throw Error('invalid_policy_identity');
 const u=new URL(entry.sourceUrl);if(u.protocol!=='https:'||u.username||u.password)throw Error('invalid_policy_url');
 const policy=Object.freeze({...entry,rights:Object.freeze({...entry.rights})});
 map.set(policy.policyId,policy);
 }
 return Object.freeze({resolve(id,input,asOf){
 const policy=map.get(id);if(!policy)throw Error('unknown_policy');
 observation(input,policy,asOf);
 return policy;
 }});
}
