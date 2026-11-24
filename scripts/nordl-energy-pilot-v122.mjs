// Private candidate; source snapshot time is not measurement/publication time.
import {observation} from './nordl-observation-v122.mjs';
const url='https://api.nve.no/doc/magasinstatistikk/';
function weekEnd(y,w){
 if(!Number.isInteger(y)||y<1995||y>2100||!Number.isInteger(w)||w<1||w>53)throw Error('invalid_week');
 const jan4=new Date(Date.UTC(y,0,4)), monday=jan4.getTime()-((jan4.getUTCDay()+6)%7)*86400000;
 const thursday=new Date(monday+((w-1)*7+3)*86400000);
 if(thursday.getUTCFullYear()!==y)throw Error('invalid_iso_week');
 return new Date(monday+((w-1)*7+6)*86400000).toISOString().slice(0,10);
}
export function energyPilot(snapshot,asOf){
 const results=[],missing=[];
 for(const zone of ['NO1','NO2','NO3','NO4','NO5']){
 try{
 const r=snapshot.reservoirs,z=r.zones[zone],end=weekEnd(r.year,r.week);
 if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?(?:Z|\+00:00)$/.test(snapshot.generated))throw Error('invalid_snapshot_time');
 const retrievedAt=new Date(snapshot.generated).toISOString();
 if(Date.parse(asOf)-Date.parse(end)>35*86400000||!Number.isInteger(z.years)||z.years<10||![z.fill,z.normal].every(v=>typeof v==='number'&&Number.isFinite(v)&&v>=0&&v<=1))throw Error('ineligible_reference');
 const make=(metric,value)=>{
 const policy={policyId:'nve-reservoir-private-pilot-v1',sourceId:'nve',seriesId:'reservoir:'+zone+':'+metric,entityId:'bidding-zone:'+zone,metric,unit:'percent',sourceUrl:url,evidence:'Energy hydro_archive.py source and NLOD reference; candidate only',rights:{collect:'allowed',retain:'unreviewed',display:'unreviewed',export:'unreviewed'}};
 return observation({...policy,value,periodEnd:end,retrievedAt},policy,asOf);
 };
 const actual=make('reservoir-fill',z.fill*100),reference=make('reported-seasonal-reference',z.normal*100);
 results.push({zone,actual,reference,referenceYears:z.years,signal:{kind:'seasonal_reference_difference',algorithm:'nve-reference-pp-v1',inputRevisionIds:[actual.revisionId,reference.revisionId],differencePercentagePoints:Math.round((actual.value-reference.value)*100)/100,publicEligible:false,limitation:'Reported seasonal reference; underlying vintages not validated here. Not a price forecast.'}});
 }catch{missing.push({zone,reason:'unavailable_or_invalid'});}
 }
 return {schemaVersion:1,asOf,results,missing,publicEligible:false};
}
