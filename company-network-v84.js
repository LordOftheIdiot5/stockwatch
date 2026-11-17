/* Evidence-linked company network. Never promote review candidates to edges. */
(function(global){'use strict';
const types={supplies:'Supply',supply_contract:'Supply contract',service_contract:'Service contract',equity_investment:'Equity investment',financing:'Financing',debt_repayment:'Debt repayment',arrangement:'Financing arrangement'};
const colors={supplies:'#249b83',supply_contract:'#249b83',service_contract:'#b88a40',equity_investment:'#4d87db',financing:'#4d87db',debt_repayment:'#4d87db',arrangement:'#8a7bb8'};
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const validDate=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x;
const https=x=>{try{const u=new URL(x);return u.protocol==='https:'&&!u.username&&!u.password?u.href:null}catch{return null}};
function graph(data){
 const nodes=new Map(),edgeIds=new Set(),edges=[];
 if(data?.schemaVersion!==1||!validDate(data.compiledOn))return {nodes,edges};
 for(const n of data.entities||[]){
  if(!n||!/^[-a-z0-9]+$/.test(n.id)||typeof n.name!=='string'||!n.name||nodes.has(n.id))continue;
  nodes.set(n.id,n);
 }
 for(const e of data.relationships||[]){
  if(!e||!e.id||edgeIds.has(e.id)||!nodes.has(e.from)||!nodes.has(e.to)||e.from===e.to||!Object.hasOwn(types,e.type)||e.evidenceStatus!=='issuer_disclosed'||e.actualCashFlow!==false||!validDate(e.disclosedOn)||!validDate(e.reviewedOn)||e.disclosedOn>e.reviewedOn||e.reviewedOn>data.compiledOn||!https(e.sourceUrl)||typeof e.sourceLocator!=='string'||!e.sourceLocator||typeof e.subject!=='string'||!e.subject)continue;
  const a=e.amount;if(a!==null&&(!a||!Number.isSafeInteger(a.value)||a.value<=0||!/^[A-Z]{3}$/.test(a.currency)||!['exact_reported','greater_than','approximate','up_to'].includes(a.comparison)||!a.basis))continue;
  edgeIds.add(e.id);edges.push(e);
 }
 return {nodes,edges};
}
function neighborhood(g,id,kind='all',hops=1){
 if(!g.nodes.has(id))return {nodes:[],edges:[]};
 const allowed=g.edges.filter(e=>kind==='all'||e.type===kind),seen=new Set([id]);
 for(let i=0;i<hops;i++){const prior=new Set(seen);for(const e of allowed){if(prior.has(e.from)||prior.has(e.to)){seen.add(e.from);seen.add(e.to)}}}
 const edges=allowed.filter(e=>seen.has(e.from)&&seen.has(e.to)&&(hops>1||e.from===id||e.to===id));
 return {nodes:[...seen].map(i=>g.nodes.get(i)),edges};
}
function amountLabel(a){
 if(!a)return 'Amount not disclosed';
 const scale=a.value>=1e9?[1e9,'bn']:a.value>=1e6?[1e6,'m']:[1,''];
 return (a.comparison==='greater_than'?'> ':a.comparison==='approximate'?'≈ ':a.comparison==='up_to'?'Up to ':'')+a.currency+' '+(a.value/scale[0]).toLocaleString('en-US',{maximumFractionDigits:3})+(scale[1]?' '+scale[1]:'')+' · '+a.basis.replaceAll('_',' ');
}
function photo(data,listing){
 const rows=(data?.assets||[]).filter(a=>a?.listing===listing&&a.status==='imported'&&/^[a-z0-9-]+$/.test(a.id)&&a.localAsset==='assets/company/'+a.id+'.webp'&&Number.isInteger(a.width)&&a.width>0&&Number.isInteger(a.height)&&a.height>0&&Number.isInteger(a.bytes)&&a.bytes<=256000&&https(a.sourcePage)&&https(a.licenseUrl)&&a.author&&a.license&&a.caption&&a.alt);
 if(rows.length!==1)return '';
 const a=rows[0];return '<figure class="sw-company-photo"><img src="'+esc(a.localAsset)+'" alt="'+esc(a.alt)+'" width="'+a.width+'" height="'+a.height+'" loading="lazy" decoding="async"><figcaption>'+esc(a.caption)+' · '+esc(a.capturedOn)+' · '+esc(a.author)+' · <a href="'+esc(a.sourcePage)+'" target="_blank" rel="noopener noreferrer">Original photograph</a> · <a href="'+esc(a.licenseUrl)+'" target="_blank" rel="noopener noreferrer">'+esc(a.license)+'</a> · Resized / WebP</figcaption></figure>';
}
function mapHTML(g,selected,edges){
 const center=g.nodes.get(selected);if(!center)return '';
 const incoming=edges.filter(e=>e.to===selected),outgoing=edges.filter(e=>e.from===selected);
 const group=(rows,side)=>rows.length?rows.map(e=>{const id=side==='in'?e.from:e.to,n=g.nodes.get(id);return '<button type="button" class="sw-network-node" data-network-entity="'+esc(id)+'" style="--edge-color:'+colors[e.type]+'"><strong>'+esc(n.name)+'</strong><small>'+esc(types[e.type])+' · '+esc(e.subject)+'</small><span>'+esc(amountLabel(e.amount))+'</span></button>'}).join(''):'<p class="sw-meta">No documented connections in this direction.</p>';
 return '<div class="sw-network-map"><div class="sw-network-side"><h3>Incoming →</h3>'+group(incoming,'in')+'</div><div class="sw-network-center"><small>SELECTED COMPANY</small><strong>'+esc(center.name)+'</strong><small>'+esc(center.listingId||'No mapped stock listing')+'</small></div><div class="sw-network-side"><h3>→ Outgoing</h3>'+group(outgoing,'out')+'</div></div>';
}
function edgeHTML(g,e){
 return '<article class="sw-peer sw-network-evidence"><small>'+esc(types[e.type])+' · disclosed '+esc(e.disclosedOn)+'</small><strong>'+esc(g.nodes.get(e.from).name)+' → '+esc(g.nodes.get(e.to).name)+'</strong><span>'+esc(e.subject)+'</span><b>'+esc(amountLabel(e.amount))+'</b>'+(e.conditions?'<small>'+esc(e.conditions)+'</small>':'')+(e.deliveryWindow?'<small>Expected delivery: '+esc(e.deliveryWindow)+'</small>':'')+'<a class="sw-textlink" href="'+esc(https(e.sourceUrl))+'" target="_blank" rel="noopener noreferrer">'+esc(e.sourceLocator)+' ↗</a></article>';
}
function mount(root,data,{selected=null,review=null,photos=null}={}){
 if(!root)return;const g=graph(data);if(!g.nodes.size){root.innerHTML='<p class="sw-meta">Documented commercial network unavailable.</p>';return;}
 let id=g.nodes.has(selected)?selected:g.nodes.has('nvidia')?'nvidia':[...g.nodes.keys()][0],kind='all',hops=1;
 root.innerHTML='<section class="sw-panel sw-network-panel"><div class="sw-panel-hd"><div><h2>Commercial &amp; capital relationships</h2><small>'+g.nodes.size+' entities · '+g.edges.length+' documented relationships</small></div></div><div class="sw-panel-pad"><p class="sw-meta">Supply arrows show goods or services; investment and financing arrows show announced capital relationships. Contract amounts are not realized cash, sales or guaranteed revenue. Unmapped and private entities are included without inventing prices.</p><div class="sw-controls"><label>Company <select data-network-select aria-label="Select company">'+[...g.nodes.values()].sort((a,b)=>a.name.localeCompare(b.name)).map(n=>'<option value="'+esc(n.id)+'">'+esc(n.name)+'</option>').join('')+'</select></label><label>Relationship <select data-network-kind aria-label="Relationship type"><option value="all">All types</option>'+Object.entries(types).map(([k,v])=>'<option value="'+k+'">'+esc(v)+'</option>').join('')+'</select></label><label>Depth <select data-network-hops aria-label="Network depth"><option value="1">Direct</option><option value="2">Two hops</option></select></label></div><div data-network-view></div><div data-network-records></div><p class="sw-meta">'+(Array.isArray(review?.candidates)?review.candidates.length+' unverified news review leads are stored separately. ':'')+'Never infer a commercial relationship from a headline alone.</p></div></section>';
 const select=root.querySelector('[data-network-select]'),filter=root.querySelector('[data-network-kind]'),depth=root.querySelector('[data-network-hops]');
 function render(){
  select.value=id;const n=neighborhood(g,id,kind,hops),center=g.nodes.get(id);
  const photoHTML=center.listingId?photo(photos,center.listingId):'';
  root.querySelector('[data-network-view]').innerHTML=photoHTML+mapHTML(g,id,n.edges)+(hops===2?'<p class="sw-meta">Two-hop evidence includes connections between adjacent companies below.</p>':'');
  root.querySelector('[data-network-records]').innerHTML='<div class="sw-section-row"><h3>Source-backed connections</h3><small>'+n.edges.length+' records</small></div><div class="sw-intel-mini">'+(n.edges.map(e=>edgeHTML(g,e)).join('')||'<p class="sw-meta">No documented relationships match this filter.</p>')+'</div>';
 }
 select.addEventListener('change',()=>{id=select.value;render()});filter.addEventListener('change',()=>{kind=filter.value;render()});depth.addEventListener('change',()=>{hops=Number(depth.value);render()});root.addEventListener('click',e=>{const b=e.target.closest('[data-network-entity]');if(b&&g.nodes.has(b.dataset.networkEntity)){id=b.dataset.networkEntity;render()}});render();
}
function entityForListing(data,listing){return typeof listing==='string'&&listing?(data?.entities||[]).find(n=>typeof n.listingId==='string'&&(n.listingId===listing||'ref:'+n.listingId===listing))?.id||null:null}
const api={graph,neighborhood,amountLabel,photo,mount,entityForListing};if(typeof module==='object'&&module.exports)module.exports=api;else global.StockwatchRelationships=api;
})(typeof window!=='undefined'?window:{});
