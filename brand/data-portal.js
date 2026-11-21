/* Commercial discovery: metadata only; no automatic sale, raw export or licensed feed. */
(function(global){'use strict';
const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safe=x=>{try{const u=new URL(x);return u.protocol==='https:'&&!u.username&&!u.password?u.href:''}catch{return ''}};
const groups={
'instrument-reference':{kind:'Listing references',fields:['figi','shareClassFIGI','compositeFIGI','ticker','mic','name','securityType'],route:'directory.html'},
'energy-spot':{kind:'Dated observations',keys:['eia:RBRTE','eia:RWTC'],fields:['seriesId','date','value','unit','sourceUrl','license'],route:'commodities.html'},
'fx':{kind:'Dated reference observations',prefix:'fx:',fields:['seriesId','date','value','unit','sourceUrl','license'],route:'commodities.html'},
'rates':{kind:'Dated observations',prefix:'fred:',fields:['seriesId','date','value','unit','sourceUrl','license'],route:'terminal.html'},
'trade':{kind:'Dated statistical observations',prefixes:['NE.EXP.','NY.GDP.','NE.IMP.'],fields:['indicatorId','country','date','value','unit','sourceUrl'],route:'terminal.html?research=official'},
'shipping':{kind:'Dated indicators',paths:['data/shipping-open.json','data/shipping-ports.json','data/shipping-connectivity.json'],fields:['seriesId','date','value','unit','frequency','sourceUrl'],route:'shipping.html'},
'euronext-history':{kind:'Infrastructure only',fields:[],route:'price-history.html'},
'company-financials':{kind:'Reported filing facts',fields:['subject','periodEnd','periodLabel','currency','metric','value','sourceUrl','revision'],route:'research.html'}
};
function catalog(data,index,coverage){
 return (data?.datasets||[]).filter(p=>p.id&&groups[p.id]&&safe(p.sourceUrl)).map(p=>{
 const g=groups[p.id],rows=(index?.datasets||[]).filter(r=>g.keys?.includes(r.id)||g.prefix&&r.id?.startsWith(g.prefix)||g.prefixes?.some(x=>r.id?.startsWith(x))||g.paths?.includes(r.path));
 const known=rows.filter(r=>Number.isSafeInteger(r.records)&&r.records>=0),count=known.length?known.reduce((a,r)=>a+r.records,0):null;
 let n=count;if(p.id==='instrument-reference')n=Array.isArray(coverage?.directory?.records)?coverage.directory.records.length:null;
 if(p.id==='company-financials')n=coverage?.fundamentals?.companies&&typeof coverage.fundamentals.companies==='object'?Object.keys(coverage.fundamentals.companies).length:null;
 return {id:p.id,title:p.title,category:p.category,description:p.description,status:p.status,sourceUrl:safe(p.sourceUrl),rights:p.accessPolicy,commercialStatus:'Agreement and source-rights review required',kind:g.kind,count:n,countUnit:p.id==='company-financials'?'company records':p.id==='instrument-reference'?'reference records':'indexed observations / records',series:rows.length||null,fields:g.fields,route:g.route};
 });
}
function exportMetadata(rows){return JSON.stringify({
 notice:'Descriptive metadata only. No underlying data, commercial redistribution entitlement, or service-level agreement.',
 products:rows.map(p=>({
  id:p.id,title:p.title,category:p.category,description:p.description,
  status:p.status,sourceUrl:p.sourceUrl,rights:p.rights,
  commercialStatus:p.commercialStatus,kind:p.kind,
  count:p.count,countUnit:p.countUnit,series:p.series,
  fields:Array.isArray(p.fields)?p.fields.slice():[]
 }))},null,2)}
function schemaPreview(row){
 return JSON.stringify({
  notice:'Proposed field-name metadata; not a sample record or active API response.',
  datasetId:row.id,
  productTitle:row.title,
  schemaStatus:'proposed metadata',
  apiAvailable:false,
  commercialRedistributionApproved:false,
  fields:Array.isArray(row.fields)?row.fields.slice():[],
  sampleRecords:[],
  sourceUrl:row.sourceUrl,
  sourceRightsReview:row.rights,
  observationCount:row.count,
  observationCountMeaning:row.countUnit,
  latestObservationTime:null,
  deliveryFrequency:null
 },null,2)
}
function inquiryLink(row){
 const single=x=>String(x??'').replace(/[\r\n\t]/g,' ').slice(0,120);
 const subject='Stockwatch dataset integration inquiry — '+single(row.title||row.id||'Research');
 const body=[
  'Hello Nordl,',
  '',
  'I would like to discuss a possible source-rights-reviewed Stockwatch data integration.',
  'Dataset: '+single(row.title)+' ('+single(row.id)+')',
  '',
  'Organization / purpose:',
  'Intended use (internal analysis, public display, or redistribution):',
  'Countries / companies / coverage:',
  'Update frequency and history range:',
  'Preferred delivery format:',
  '',
  'Please confirm feasibility, permitted uses and any commercial terms before offering delivery.'
 ].join('\n');
 return 'mailto:vidar@nordl.dev?subject='+encodeURIComponent(subject)+'&body='+encodeURIComponent(body)
}
function saveJson(name,body){
 const url=URL.createObjectURL(new Blob([body],{type:'application/json'}));
 const a=document.createElement('a');a.href=url;a.download=name;a.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
}
async function mount(host){
 const get=async p=>{try{const r=await fetch(p);return r.ok?await r.json():null}catch{return null}};
 const [data,index,directory,fundamentals]=await Promise.all(
  ['data/research-product-catalog.json','data/research-index.json',
   'data/instrument-directory.json','data/fundamentals.json'].map(get));
 const rows=catalog(data,index,{directory,fundamentals});
 const productsLoaded=Array.isArray(data?.datasets);
 host.innerHTML='<div class="metricrow">'+
 '<div class="metric"><small>Research dataset profiles</small><strong>'+rows.length+'</strong></div>'+
 '<div class="metric"><small>Commercial API</small><strong>Not launched</strong></div>'+
 '<div class="metric"><small>Public download</small><strong>Metadata only</strong></div></div>'+
 '<section class="dp-path" aria-label="Data integration and commercial availability">'+
 '<div><h2>Explore the datasets. Verify the rights. Discuss an integration.</h2>'+
 '<p>The profiles below describe available research and proposed schemas, not live paid feeds. Source-specific display, storage, API and resale rights must be reviewed separately. A successful scanner does not confirm a licensable data history.</p></div>'+
 '<div class="dp-path-actions">'+
 '<a class="dp-request" href="mailto:vidar@nordl.dev?subject=Stockwatch%20data%20integration%20inquiry">Request an integration by email</a>'+
 '<a href="https://t.me/NordlOfficial" target="_blank" rel="noopener noreferrer">Contact via Telegram</a>'+
 '</div></section>'+
 '<div class="dp-controls"><label>Search dataset profiles <input type="search" id="dpQuery" placeholder="FIGI, freight, FX, filings"></label>'+
 '<button id="dpExport" type="button">Download catalog metadata (JSON)</button></div>'+
 '<p id="dpStatus" role="status"></p><div class="grid" id="dpGrid"></div>'+
 '<section class="section dp-steps"><h2>Integration assessment — not an active API signup</h2>'+
 '<ol><li>Select the dataset and inspect its proposed field names, source and coverage.</li>'+
 '<li>Describe intended use, locations, users, frequency and any redistribution.</li>'+
 '<li>Review source-by-source collection, retention, display and export rights before terms or delivery are offered.</li>'+
 '<li>Only after approval: agree a tested delivery, contract, authentication and support plan.</li></ol>'+
 '<p><a href="research.html">Review the research methodology ↗</a> · '+
 '<a href="health.html">Inspect actual data coverage and source freshness ↗</a></p></section>';
 const grid=host.querySelector('#dpGrid'),q=host.querySelector('#dpQuery'),status=host.querySelector('#dpStatus');
 function draw(){
  const words=q.value.trim().toLowerCase().split(/\s+/).filter(Boolean);
  const selected=rows.filter(x=>words.every(w=>[x.title,x.category,x.kind,x.description,x.id].join(' ').toLowerCase().includes(w)));
  status.textContent=productsLoaded?
   selected.length+' dataset profiles · indexed counts are not unique issuers, verified live prices or licensed export coverage':
   'Product catalog unavailable. No commercial availability can be confirmed.';
  grid.innerHTML=selected.map(x=>{
   const count=x.count==null?'Coverage not quantified':x.count.toLocaleString('en-GB')+' '+x.countUnit;
   const schema=schemaPreview(x);
   return '<article class="tile dp-product" data-product-id="'+E(x.id)+'">'+
     '<small>'+E(x.category)+'</small><h3>'+E(x.title)+'</h3>'+
     '<p>'+E(x.description)+'</p><p class="dp-count"><strong>'+E(count)+'</strong></p>'+
     '<p class="dp-product-status">'+E(x.status)+'</p>'+
     '<details><summary>Inspect proposed schema and rights</summary>'+
     '<p class="dp-disclaimer">This is a field-name preview, not raw records or an active API contract.</p>'+
     '<pre class="dp-schema">'+E(schema)+'</pre>'+
     '<p><strong>Source review:</strong> '+E(x.rights)+'</p>'+
     '<p>'+E(x.commercialStatus)+'</p>'+
     '<button type="button" class="dp-schema-export" data-schema="'+E(x.id)+'">Download schema metadata</button></details>'+
     '<div class="dp-card-links"><a href="'+E(x.route)+'">Explore public research ↗</a>'+
     '<a href="'+E(x.sourceUrl)+'" target="_blank" rel="noopener noreferrer">Original source ↗</a>'+
     '<a class="dp-contact-link" href="'+E(inquiryLink(x))+'">Ask about this dataset ↗</a></div></article>'
  }).join('')||'<p>No matching dataset profiles. Change your search or contact Nordl about a proposed source.</p>';
 }
 grid.addEventListener('click',event=>{
  const button=event.target.closest('button[data-schema]');
  if(!button||!grid.contains(button))return;
  const row=rows.find(x=>x.id===button.dataset.schema);
  if(row)saveJson('stockwatch-'+row.id+'-schema-metadata.json',schemaPreview(row));
 });
 q.oninput=draw;draw();
 host.querySelector('#dpExport').onclick=()=>saveJson('stockwatch-catalog-metadata.json',exportMetadata(rows));
}
const api={catalog,exportMetadata,schemaPreview,inquiryLink};
if(typeof module==='object'&&module.exports)module.exports=api;
else{const host=document.getElementById('dataPortal');if(host)mount(host)}
})(typeof window!=='undefined'?window:{});
