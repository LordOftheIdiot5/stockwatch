/* Existing published official observations only; research hypotheses are not measured exposures. */
(function(global){'use strict';
const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const safe=x=>{try{let u=new URL(x);return u.protocol==='https:'&&!u.username&&!u.password?u.href:''}catch{return ''}};
const num=x=>typeof x==='number'&&Number.isFinite(x);
const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x;
function profile(config,sector,ticker){
 const profiles=config?.driverProfiles||[],p=profiles.find(x=>x.sectors?.includes(sector));
 if(!p)return null;
 // Only sector contexts are inferred. Issuer-specific overrides remain subject to separate review.
 return {...p,drivers:p.drivers.map(d=>({...d,datasets:(d.datasetIds||[]).map(id=>(config.datasets||[]).find(x=>x.id===id)).filter(Boolean)}))};
}
function observations(rows){const m=new Map(),bad=new Set();for(const r of rows||[]){if(!day(r?.date)||!num(r.value))continue;if(m.has(r.date)&&m.get(r.date)!==r.value)bad.add(r.date);else m.set(r.date,r.value)}return [...m].filter(([d])=>!bad.has(d)).sort(([a],[b])=>a.localeCompare(b)).map(([date,value])=>({date,value}))}
function describe(d,payload){
 if(!payload)return {status:'Unavailable'};
 if(d.file==='data/free-research.json'){
  const x=(payload.datasets||[]).find(x=>x.id===d.key);
  return x?{status:x.status||'Unknown',count:Array.isArray(x.records)?x.records.length:0,source:safe(x.sourceUrl),license:x.license,period:x.retrievedAt,recordOnly:true}:{status:'Not found'};
 }
 if(!d.key){const count=Array.isArray(payload.series)?payload.series.length:0;return {status:count?'Published structured series':'No observations confirmed',count,source:safe(payload.sourceUrl),license:payload.license,recordOnly:true}}
 const x=(payload.series||[]).find(s=>s.key===d.key);if(!x)return {status:'Not found'};
 const p=observations(x.history),source=safe(x.sourceUrl),license=typeof x.license==='string'?x.license:'';
 return {status:p.length?'Published observations':'No dated observations confirmed',count:p.length,source,license,frequency:x.frequency,unit:x.unit,period:p.at(-1)?.date,points:source&&license&&x.unit?p:[],label:x.label||d.label};
}
function mount(host,{config,sector,ticker,load}){
 const p=profile(config,sector,ticker);if(!p){host.innerHTML='<p class="sw-meta">No curated sector-driver profile yet.</p>';return}
 host.innerHTML='<h2>Industry drivers</h2><p class="sw-meta">Research questions for this sector. These are not confirmed company exposures, causal relationships, forecasts or investment recommendations.</p><div class="sw55-drivers">'+p.drivers.map((d,i)=>'<details data-driver="'+i+'"><summary><small>'+E(d.category)+'</small><strong>'+E(d.label)+'</strong><span>'+d.datasets.length+' contextual sources</span></summary><div class="sw55-detail"><p>'+E(d.question)+'</p><p class="sw-meta">Coverage gap: '+E(d.missing)+'</p><div data-driver-results></div></div></details>').join('')+'</div>';
 const cache=new Map();
 const get=d=>{if(!/^data\/(?:economic-feeds|open-data|shipping-open|shipping-ports|shipping-connectivity|entsoe-open|free-research)\.json$/.test(d.file))return Promise.resolve(null);if(!cache.has(d.file))cache.set(d.file,Promise.resolve().then(()=>load(d.file)).catch(()=>null));return cache.get(d.file)};
 host.querySelectorAll('[data-driver]').forEach(detail=>detail.addEventListener('toggle',async()=>{
  if(!detail.open||detail.dataset.loaded)return;detail.dataset.loaded='true';
  const d=p.drivers[Number(detail.dataset.driver)],out=detail.querySelector('[data-driver-results]');
  if(!d.datasets.length){out.textContent='No connected source for this research question.';return}
  out.textContent='Checking published records…';
  const records=await Promise.all(d.datasets.map(async x=>({d:x,r:describe(x,await get(x))})));
  if(!host.contains(detail))return;
  out.replaceChildren();
  records.forEach(({d:x,r},j)=>{
   const card=document.createElement('div');card.className='sw55-source';
   card.innerHTML='<strong>'+E(x.label)+'</strong><p class="sw-meta">'+E(r.status)+' · '+E(r.count??0)+' records/observations'+(r.period?' · '+E(r.recordOnly?'Retrieved '+r.period:r.period):'')+(r.unit?' · '+E(r.unit):'')+'</p><p class="sw-meta">'+E(r.license||'Reuse rights not documented here')+'</p>'+(r.source?'<a class="sw-textlink" href="'+E(r.source)+'" target="_blank" rel="noopener noreferrer">Original source ↗</a> ':'')+(/^([a-z-]+)\.html(?:\?research=official)?$/.test(x.href)?'<a class="sw-textlink" href="'+E(x.href)+'">Explore dataset ↗</a>':'');
   if(r.points?.length>=2&&global.StockwatchNativeChart){const b=document.createElement('button'),plot=document.createElement('div');b.type='button';b.className='sw-soft-btn';b.textContent='Show dated observations';plot.id='sw55-'+String(ticker).replace(/[^a-z0-9]/gi,'-')+'-'+detail.dataset.driver+'-'+j;b.addEventListener('click',()=>{if(plot.childNodes.length){plot.replaceChildren();b.textContent='Show dated observations'}else{global.StockwatchNativeChart.mount(plot,{label:r.label,unit:r.unit,series:[{label:r.label,unit:r.unit,points:r.points}],source:r.source,notice:'Official original units · '+(r.frequency||'Frequency not recorded')+' · not a measured issuer exposure'});b.textContent='Hide chart'}});card.append(b,plot)}
   out.append(card)
  });
 }));
}
const api={profile,observations,describe,mount};if(typeof module==='object'&&module.exports)module.exports=api;else global.StockwatchIndustry=api;
})(typeof window!=='undefined'?window:{});
