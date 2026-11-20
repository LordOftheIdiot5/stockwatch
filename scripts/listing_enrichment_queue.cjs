/* Unified, deterministic enrichment work queue. No provider or permission is inferred. */
'use strict';
const fs=require('node:fs'),path=require('node:path');
const PRICE_ROUTES={Stockholm:'nasdaq_nordic',Copenhagen:'nasdaq_nordic',Helsinki:'nasdaq_nordic',Oslo:'euronext',Paris:'euronext',Amsterdam:'euronext',Brussels:'euronext',Milan:'euronext',Irish:'euronext',Dublin:'euronext',Lisbon:'euronext'};
function build(inventory){
 if(!Array.isArray(inventory.records)||inventory.records.length!==inventory.summary?.listings||!inventory.records.length)throw Error('Invalid inventory');
 const seen=new Set(),totals={},records=[];
 for(const r of inventory.records){
  if(typeof r.id!=='string'||!r.id||seen.has(r.id))throw Error('Duplicate or missing listing ID');
  seen.add(r.id);
  const exact=r.identityStatus==='isin_and_mic'&&!!r.isin&&!!r.mic;
  const route=PRICE_ROUTES[r.venue]||'venue_specific';
  const hasPrice=r.priceStatus!=='missing'&&!!r.priceDate;
  const tasks={
   identity:exact?'evidence_present':'resolve_identity',
   price:hasPrice?'dated_observation_present':exact?'review_authorized_price_route':'await_identity',
   historical_prices:r.licensedHistory?'licensed_history_present':exact?'review_retention_and_collect':'await_identity',
   news:r.newsRecords>0?'archive_matches_present':'match_issuer_and_collect',
   financials:r.fundamentalsAvailable?'observations_present':'resolve_issuer_then_collect_filings',
   sector:r.sector?'classification_present':'classify_from_evidence',
   description:r.descriptionAvailable?'description_present':'build_source_linked_profile',
   operating:r.operatingMetricsAvailable?'observations_present':'review_sector_metrics'
  };
  for(const [k,v] of Object.entries(tasks)){totals[k]??={};totals[k][v]=(totals[k][v]||0)+1}
  records.push({id:r.id,name:r.name,venue:r.venue,group:r.group,mic:r.mic||null,isin:r.isin||null,figi:r.figi||null,priceRoute:route,priceDate:hasPrice?r.priceDate:null,tasks});
 }
 return {schemaVersion:1,generated:inventory.generated,listings:records.length,totals,records,notice:'Work routing only. No new network requests, verified freshness, provider permissions, or completed profiles implied. New inventory IDs enter automatically; source-specific approval and exact identity remain required.'};
}
function write(inventory,root){const out=build(inventory),dest=path.join(root,'data/listing-enrichment-queue-v1.json');fs.writeFileSync(dest+'.tmp',JSON.stringify(out,null,2)+'\n');fs.renameSync(dest+'.tmp',dest);console.log('LISTING_ENRICHMENT '+JSON.stringify({listings:out.listings,totals:out.totals}));return out}
module.exports={build,write};
