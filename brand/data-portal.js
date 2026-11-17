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
function exportMetadata(rows){return JSON.stringify({notice:'Descriptive metadata only. No underlying data, commercial redistribution entitlement, or service-level agreement.',products:rows.map(({route,...p})=>p)},null,2)}
async function mount(host){
 const get=async p=>{try{const r=await fetch(p);return r.ok?await r.json():null}catch{return null}};
 const [data,index,directory,fundamentals]=await Promise.all(['data/research-product-catalog.json','data/research-index.json','data/instrument-directory.json','data/fundamentals.json'].map(get));
 const rows=catalog(data,index,{directory,fundamentals});
 host.innerHTML='<div class="metricrow"><div class="metric"><small>Research product profiles</small><strong>'+rows.length+'</strong></div><div class="metric"><small>Commercial access</small><strong>By agreement</strong></div><div class="metric"><small>Public export</small><strong>Metadata only</strong></div></div><div class="dp-controls"><label>Search products <input type="search" id="dpQuery" placeholder="FIGI, shipping, energy, statements"></label><button id="dpExport" type="button">Export catalog JSON</button></div><p id="dpStatus" role="status"></p><div class="grid" id="dpGrid"></div><section class="section"><h2>Proposed integration workflow</h2><p class="muted">1. Identify required datasets, geography and history. 2. Verify source-specific retention, processing and onward distribution rights. 3. Agree delivery format, update frequency and commercial terms. An authenticated commercial data API is not yet enabled.</p></section>';
 const grid=host.querySelector('#dpGrid'),q=host.querySelector('#dpQuery'),status=host.querySelector('#dpStatus');
 function draw(){const words=q.value.trim().toLowerCase().split(/\s+/).filter(Boolean),r=rows.filter(x=>words.every(w=>[x.title,x.category,x.kind,x.description].join(' ').toLowerCase().includes(w)));status.textContent=r.length+' product profiles · counts describe indexed snapshots, not unique issuers or licensed coverage';grid.innerHTML=r.map(x=>'<article class="tile dp-product"><small>'+E(x.category)+'</small><h3>'+E(x.title)+'</h3><p>'+E(x.description)+'</p><strong>'+E(x.count==null?'Coverage not quantified':x.count.toLocaleString('en-GB')+' '+x.countUnit)+'</strong><p>'+E(x.status)+'</p><details><summary>Schema &amp; permitted access</summary><p>Proposed normalized fields, not an active API contract.</p><p>'+E(x.fields.join(' · ')||'No downloadable schema')+'</p><p>'+E(x.rights)+'</p><p>'+E(x.commercialStatus)+'</p></details><a href="'+E(x.route)+'">Explore public research ↗</a><a href="'+E(x.sourceUrl)+'" target="_blank" rel="noopener noreferrer">Primary source ↗</a></article>').join('')||'<p>No matching products.</p>'}
 q.oninput=draw;draw();
 host.querySelector('#dpExport').onclick=()=>{const u=URL.createObjectURL(new Blob([exportMetadata(rows)],{type:'application/json'})),a=document.createElement('a');a.href=u;a.download='stockwatch-catalog-metadata.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};
}
const api={catalog,exportMetadata};if(typeof module==='object'&&module.exports)module.exports=api;else{const host=document.getElementById('dataPortal');if(host)mount(host)}
})(typeof window!=='undefined'?window:{});
