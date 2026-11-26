/* V89f phase 1: a collection queue, not a quote feed or grant of rights. */
'use strict';
const fs=require('node:fs'),path=require('node:path');
const groups={
 nasdaq_nordic:{venues:['Stockholm','Copenhagen','Helsinki'],provider:'Nasdaq Nordic',source:'https://tradereports.nasdaq.com/',policy:'https://www.nasdaq.com/market-regulation/nordic/mifid-ii',status:'private_analysis_confirmed_report_access_unverified',rightsEvidenceDate:'2026-11-25',privateAnalysisConfirmed:true,reportAccessVerified:false,publicDisplayReview:'pending_scope_and_agreement',retentionReview:'pending'},
 euronext:{venues:['Oslo','Paris','Amsterdam','Brussels','Milan','Irish','Lisbon'],provider:'Euronext',source:'https://marketdata.euronext.com/data-reporting-service/trades-file',policy:'https://www.euronext.com/en/data/real-time-data/pricing-specs-agreements/market-data-pricing-policies',status:'public_distribution_not_confirmed',privateAnalysisConfirmed:true,reportAccessVerified:true},
 other:{venues:[],provider:'Venue-specific review',source:null,policy:null,status:'source_selection_required',privateAnalysisConfirmed:false,reportAccessVerified:false}
};
const alternative={provider:'Cboe Europe',product:'End-of-day equities data',policy:'https://cdn.cboe.com/resources/participant_resources/Cboe_Europe_Data_Policy_August_2026.pdf',source:'https://www.cboe.com/markets/eu/equities/transparency-data/',status:'eod_distribution_exemption_identified_access_and_retention_unconfirmed',note:'EOD distribution is exempt in the policy; delayed transparency downloads have separate use terms. Do not treat alternate-venue executions as primary-exchange closes.'};
function validISIN(value){
 if(typeof value!=='string'||!/^[A-Z]{2}[A-Z0-9]{9}[0-9]$/.test(value))return false;
 const digits=[...value].map(c=>/[A-Z]/.test(c)?String(c.charCodeAt(0)-55):c).join('');
 let sum=0;for(let i=digits.length-1,twice=false;i>=0;i--,twice=!twice){const n=Number(digits[i])*(twice?2:1);sum+=n>9?n-9:n;}
 return sum%10===0;
}
function validMIC(value){return typeof value==='string'&&/^[A-Z0-9]{4}$/.test(value)}
function build(inventory){
 if(!Array.isArray(inventory.records)||inventory.records.length!==inventory.summary?.listings)throw Error('Invalid coverage inventory');
 const ids=new Set(),queues=Object.fromEntries(Object.entries(groups).map(([k,v])=>[k,{...v,missing:0,readiness:{isinMic:0,figiMicWithoutISIN:0,otherIdentity:0},records:[]}]));
 for(const row of inventory.records){
  if(!row.id||ids.has(row.id))throw Error('Missing or duplicate listing ID');ids.add(row.id);
  if(row.priceStatus!=='missing')continue;
  const group=Object.keys(groups).find(k=>groups[k].venues.includes(row.venue))||'other';
  const q=queues[group];q.missing++;
  const exact=validISIN(row.isin)&&validMIC(row.mic),figiOnly=!exact&&validMIC(row.mic)&&typeof row.figi==='string'&&/^[A-Z0-9]{12}$/.test(row.figi);
  const readiness=exact?'isinMic':figiOnly?'figiMicWithoutISIN':'otherIdentity';q.readiness[readiness]++;
  q.records.push({id:row.id,venue:row.venue,mic:row.mic||null,isin:row.isin||null,figi:row.figi||null,identityStatus:row.identityStatus||null,
    identityReadiness:readiness,
    next:exact?'review_provider_mapping_and_rights':figiOnly?'resolve_exact_isin_for_figi_and_mic':'complete_identity_evidence',
    collectionEnabled:false,publicDisplayApproved:false,historicalRetentionApproved:false,commercialExportApproved:false});
 }
 if(Object.values(queues).reduce((n,q)=>n+q.missing,0)!==inventory.summary.missingPrice)throw Error('Missing-price denominator mismatch');
 return {schemaVersion:1,generated:inventory.generated,missingPrice:inventory.summary.missingPrice,queues,alternative,
 notice:'Candidate source routing only; no new prices collected. Coverage and venue access are not guaranteed. Missing rows are UI listing IDs, not deduplicated securities. All new source activation remains disabled pending exact mapping, access and rights review.'};
}
function write(inventory,root){const out=build(inventory),dest=path.join(root,'data/price-source-queue-v1.json');fs.writeFileSync(dest+'.tmp',JSON.stringify(out,null,2)+'\n');fs.renameSync(dest+'.tmp',dest);console.log('PRICE_SOURCE_QUEUE '+JSON.stringify(Object.fromEntries(Object.entries(out.queues).map(([k,v])=>[k,v.missing]))));return out}
module.exports={build,write,validISIN};
