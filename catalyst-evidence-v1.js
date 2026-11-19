/* V89d: historical catalyst evidence. DOM text only; no raw HTML injection. */
(()=>{'use strict';
const host=document.getElementById('catalystEvidence');if(!host)return;
const details=document.getElementById('catalystPanel');let started=false;
const make=(tag,text,cls)=>{const node=document.createElement(tag);if(text!=null)node.textContent=text;if(cls)node.className=cls;return node};
const labels={reviewed_disclosure:'Reviewed disclosure',issuer_headline:'Issuer headline · review required',media_lead:'Media lead · review required'};
function safe(url){try{const u=new URL(url);return u.protocol==='https:'&&!u.username&&!u.password?u.href:null}catch{return null}}
function filter(data){
 const controls=make('div',null,'sw-panel-pad'),summary=make('p',null,'sw-meta'),results=make('div',null,'sw-panel-pad');
 const rows=Array.isArray(data.items)?data.items:[];const select=make('select'),topic=make('select'),search=make('input');
 function opt(target,value,label){const n=make('option',label);n.value=value;target.append(n)}
 opt(select,'all','All evidence');for(const [k,v] of Object.entries(labels))opt(select,k,v);
 opt(topic,'all','All event topics');for(const k of [...new Set(rows.map(r=>r.category))].sort())opt(topic,k,k.replaceAll('_',' '));
 select.setAttribute('aria-label','Evidence status');topic.setAttribute('aria-label','Event category');search.type='search';search.placeholder='Company or ticker';search.setAttribute('aria-label','Search catalyst companies');
 controls.append(select,topic,search,summary);host.replaceChildren(controls,results);
 function draw(){const q=search.value.trim().toLowerCase();const matching=rows.filter(r=>(select.value==='all'||r.evidenceStatus===select.value)&&(topic.value==='all'||r.category===topic.value)&&[r.company,r.counterparty,r.listingId,r.counterpartyListingId].some(v=>String(v||'').toLowerCase().includes(q)));
 summary.textContent=matching.length+' matching retained evidence records · showing newest 50 · archive scan '+(data.generated||'date unavailable');
 results.replaceChildren();
 if(!matching.length){results.append(make('p','No matching retained evidence. This does not establish that no events occurred.','sw-meta'));return}
 for(const r of matching.slice(0,50)){const a=make('article',null,'sw-panel-pad');const title=make('strong',[r.company,r.counterparty].filter(Boolean).join(' → '));a.append(title,make('p',(labels[r.evidenceStatus]||'Evidence')+' · '+String(r.category).replaceAll('_',' ')+' · '+String(r.publishedAt||r.disclosedOn||'').slice(0,10),'sw-meta'));
 if(r.description)a.append(make('p',r.description));
 if(r.amount)a.append(make('p','Reported amount: '+[r.amount.comparison,r.amount.value,r.amount.currency,r.amount.basis].filter(v=>v!=null).join(' · ')+' · not cash flow','sw-meta'));
 const href=safe(r.sourceUrl);if(href){const link=make('a','Open original evidence ↗','sw-textlink');link.href=href;link.target='_blank';link.rel='noopener noreferrer';a.append(link)}
 results.append(a)}
 }
 for(const el of [select,topic,search])el.addEventListener(el===search?'input':'change',draw);draw();
}
async function load(){if(started||!details.open)return;started=true;try{const r=await fetch('data/catalyst-evidence-v1.json',{cache:'no-cache'});if(!r.ok)throw Error('not published');filter(await r.json())}catch{host.textContent='Catalyst evidence snapshot unavailable. Existing news and historical archives remain available.';started=false}}
details.addEventListener('toggle',load);load();
})();
