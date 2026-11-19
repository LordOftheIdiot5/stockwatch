/* V89e — exact-ID coverage of the current UI listing universe, never a count of distinct issuers. */
'use strict';
const fs=require('node:fs'),path=require('node:path'),{execFileSync}=require('node:child_process');
const ROOT=path.resolve(__dirname,'..');
const safeDate=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(s).toISOString().slice(0,10)===s;
const https=s=>{try{const u=new URL(s);return u.protocol==='https:'&&!u.username&&!u.password}catch{return false}};
const nonempty=s=>typeof s==='string'&&s.trim().length>0;
const index=(rows,key)=>new Map(rows.map(r=>[r[key],r]));
const realSector=s=>nonempty(s)&&!/unclassified|unknown/i.test(s);
function build(inventory,inputs){
 const {watchlist,signals,targets,expansion,issuer,coverage,fundamentals,news,operating}=inputs;
 const w=index(watchlist.tickers,'ticker'),s=index(signals.companies,'ticker'),t=index(targets.targets,'id'),i=index(issuer.entities,'ticker'),c=index(coverage.records,'id');
 const x=new Map(expansion.records.map(r=>['registry:'+r.mic+':'+r.figi,r]));
 const op=index(operating.companies,'ticker');
 const items=new Map();
 for(const r of news){
  if(!r||!nonempty(r.id)||!nonempty(r.ticker)||!https(r.url)||r.duplicateOf||!['strong','mentioned'].includes(r.relevance)||r.sourceFeed==='sec_edgar')continue;
  if(!Number.isFinite(Date.parse(r.published))||Date.parse(r.published)>Date.parse(signals.generated))continue;
  if(!items.has(r.ticker))items.set(r.ticker,new Set());
  items.get(r.ticker).add(r.id);
 }
 const ids=new Set();
 const records=inventory.records.map(r=>{
  if(ids.has(r.id))throw Error('Duplicate UI listing ID: '+r.id);
  ids.add(r.id);
  const group=w.has(r.id)?'monitored':r.id.startsWith('ref:')?'target':'registry';
  const primary=group==='monitored'?w.get(r.id):group==='target'?t.get(r.id.slice(4)):x.get(r.id);
  if(!primary)throw Error('Unmatched listing: '+r.id);
  const quote=group==='monitored'?s.get(r.id):null;
  const targetEvidence=group==='target'?c.get(r.id.slice(4)):null;
  const issuerRow=group==='monitored'?i.get(r.id):null;
  const isin=r.isin||primary.isin||issuerRow?.isin||null;
  const mic=r.mic||primary.mic||null;
  const figi=r.figi||null;
  const f=fundamentals.companies[r.id];
  const hasFundamentals=!!(f&&https(f.sourceUrl)&&safeDate(f.asOf)&&nonempty(f.currency)&&Object.values(f.metrics||{}).some(Number.isFinite));
  const hasOperating=!!op.get(r.id)?.series?.some(y=>y.observations?.some(z=>Number.isFinite(z.value)&&https(z.sourceUrl)));
  const status=r.status==='missing'?'missing':r.status;
  const hasPrice=status!=='missing'&&safeDate(r.date)&&r.date<=signals.generated.slice(0,10);
  const history=inventory.historyCoverage||{};
  const licensedHistory=(history.licensedEquityHistory?.details||[]).some(h=>h.ticker===r.id&&Number(h.observations)>0)||(history.licensedReferenceHistory?.details||[]).some(h=>h.listingId===r.id&&Number(h.observations)>0);
  return {id:r.id,name:r.name,venue:r.venue,group,mic,isin,figi,
   figiStatus:figi?(group==='target'?'candidate':'reference_record'):'missing',
   identityStatus:isin&&mic?'isin_and_mic':figi&&mic?'figi_and_mic':mic?'mic_only':'legacy_ticker',
   priceStatus:hasPrice?status:'missing',priceDate:hasPrice?r.date:null,
   licensedHistory,sector:realSector(primary.sector)?primary.sector:null,
   descriptionAvailable:nonempty(primary.description),
   newsRecords:items.get(r.id)?.size||0,newsAssociation:'exact_archive_ticker_only',
   fundamentalsAvailable:hasFundamentals,operatingMetricsAvailable:hasOperating,
   next:!hasPrice?'authorized_price_source':!isin||!mic?'identity_evidence':!hasFundamentals?'issuer_financials':!licensedHistory?'authorized_history':'enrich_profile'};
 });
 const summarize=rows=>({listings:rows.length,priced:rows.filter(r=>r.priceStatus!=='missing').length,missingPrice:rows.filter(r=>r.priceStatus==='missing').length,
  isinAndMic:rows.filter(r=>r.identityStatus==='isin_and_mic').length,figiAndMic:rows.filter(r=>r.figi&&r.mic).length,sector:rows.filter(r=>r.sector).length,
  descriptions:rows.filter(r=>r.descriptionAvailable).length,news:rows.filter(r=>r.newsRecords>0).length,fundamentals:rows.filter(r=>r.fundamentalsAvailable).length,operating:rows.filter(r=>r.operatingMetricsAvailable).length,licensedHistory:rows.filter(r=>r.licensedHistory).length});
 if(records.length!==inventory.total)throw Error('Inventory denominator mismatch');
 const byVenue=Object.fromEntries([...new Set(records.map(r=>r.venue))].sort().map(v=>[v,summarize(records.filter(r=>r.venue===v))]));
 const byGroup=Object.fromEntries(['monitored','target','registry'].map(g=>[g,summarize(records.filter(r=>r.group===g))]));
 return {schemaVersion:1,generated:signals.generated,notice:'Coverage of exact UI listing IDs, not unique issuers or verified security deduplication. Candidate FIGIs are not verified. Prices are dated observations, not proof of display or storage entitlements. News counts use exact non-SEC archive ticker IDs only; missing matches do not mean no news. Fundamentals and descriptions count only explicit fields in the inspected files. No provider requests or fabricated data.',summary:summarize(records),byVenue,byGroup,records};
}
function run(){
 const read=f=>JSON.parse(fs.readFileSync(path.join(ROOT,f),'utf8'));
 const inventory=JSON.parse(execFileSync(process.execPath,[path.join(ROOT,'scripts/audit_price_inventory.cjs')],{encoding:'utf8',maxBuffer:8*1024*1024}));
 const folder=path.join(ROOT,'data/news-store');
 const news=fs.readdirSync(folder).filter(n=>/^20\d\d-(0[1-9]|1[0-2])\.json$/.test(n)).flatMap(n=>read('data/news-store/'+n).items);
 const out=build(inventory,{watchlist:read('watchlist.json'),signals:read('data/signals.json'),targets:read('data/research-targets.json'),expansion:read('data/research-expansion.json'),issuer:read('data/issuer-identities.json'),coverage:read('data/research-coverage.json'),fundamentals:read('data/fundamentals.json'),news,operating:read('data/company-operating-metrics.json')});
 if(process.argv.includes('--write')){
  const dest=path.join(ROOT,'data/listing-coverage-v1.json');fs.writeFileSync(dest+'.tmp',JSON.stringify(out,null,2)+'\n');fs.renameSync(dest+'.tmp',dest);
  require('./price_source_queue.cjs').write(out,ROOT);
 }
 console.log(JSON.stringify({generated:out.generated,summary:out.summary,byGroup:out.byGroup,byVenue:out.byVenue},null,2));
}
module.exports={build};if(require.main===module)run();
