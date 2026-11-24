import {observation,weeklyChange} from './nordl-observation-v122.mjs';
const url='https://agtransport.usda.gov/Transportation-Costs/Grain-Transportation-Cost-Indicators/8uye-ieij';
export function shippingPilot(snapshot,asOf){
 const results=[],missing=[];
 for(const [seriesId,entityId] of [['usda:gulf-japan-index','route:us-gulf-japan'],['usda:pnw-japan-index','route:us-pnw-japan']]){
 try{
 const matches=snapshot.series.filter(s=>s.key===seriesId);
 if(matches.length!==1)throw Error('series_identity');
 const s=matches[0], unit='index, 2017 = 100';
 if(s.sourceUrl!==url||s.provider!=='USDA Agricultural Marketing Service'||s.frequency!=='weekly'||s.unit!==unit||s.baseYear!==2017||!s.license?.startsWith('USDA/AMS aggregated non-confidential, non-copyrighted source')||snapshot.source?.status!=='ok')throw Error('source_mismatch');
 const policy={policyId:'usda-aggregate-pilot-v1',sourceId:'usda-ams',seriesId,entityId,metric:'ocean-grain-cost-index',unit,sourceUrl:url,evidence:'Existing reviewed Stockwatch aggregate index archive policy; candidate computation only',rights:{collect:'allowed',retain:'unreviewed',display:'unreviewed',export:'unreviewed'}};
 if(!Array.isArray(s.history)||s.history.length<2||new Set(s.history.map(x=>x.date)).size!==s.history.length)throw Error('invalid_history');
 const h=[...s.history].sort((a,b)=>String(a.date).localeCompare(String(b.date)));
 const a=h.at(-1),b=h.at(-2);
 if(a.date!==s.period||a.value!==s.value||Date.parse(asOf)-Date.parse(a.date)>30*86400000)throw Error('stale_or_inconsistent');
 const normalize=x=>observation({...policy,periodEnd:x.date,value:x.value,retrievedAt:snapshot.generated},policy,asOf);
 const current=normalize(a),previous=normalize(b),signal=weeklyChange(current,previous);
 if(!signal)throw Error('incompatible_comparison');
 results.push({current,previous,signal});
 }catch(e){missing.push({seriesId,reason:'unavailable_or_invalid'});}
 }
 return {schemaVersion:1,asOf,results,missing,publicEligible:false};
}
