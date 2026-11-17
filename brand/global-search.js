/* Search existing public metadata, never private archives or raw quotes. */
(function(global){'use strict';
const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const norm=x=>String(x??'').toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,'').replace(/ø/g,'o').replace(/æ/g,'ae').replace(/ß/g,'ss').trim();
const safe=x=>{try{const u=new URL(x);return u.protocol==='https:'&&!u.username&&!u.password?u.href:''}catch{return ''}};
const local=(p,k,v)=>p+'?'+k+'='+encodeURIComponent(v);
function build(i={}){
 const m=new Map(),add=(kind,id,title,detail,href,terms=[])=>{if(id&&title&&href)m.set(kind+':'+id,{kind,id,title,detail,href,terms:terms.filter(Boolean).join(' ')})};
 const ids=new Map((i.issuers?.entities||[]).map(r=>[r.ticker,r])),figis=new Map((i.candidates?.figiCandidates||[]).map(r=>[r.ticker,r]));
 for(const r of i.watchlist?.tickers||[]){const a=ids.get(r.ticker),f=figis.get(r.ticker);add('Company',r.ticker,r.name,[r.ticker,r.exchange,r.sector].join(' · '),local('company.html','ticker',r.ticker),[a?.isin,a?.previousTicker,f?.figi,f?.shareClassFIGI,f?.compositeFIGI])}
 for(const r of i.directory?.records||[]){if(!r.figi||!r.mic)continue;add('Instrument',r.mic+':'+r.figi,r.name,[r.ticker,r.mic,'Reference only · not verified active listing'].join(' · '),local('directory.html','q',r.figi),[r.figi,r.shareClassFIGI,r.compositeFIGI,r.securityType,r.venue])}
 for(const r of i.news?.items||[])add('News',r.id,r.headline||r.english,[r.ticker,r.publisher,r.published,r.match].filter(Boolean).join(' · '),safe(r.url),[r.name,r.english,r.type,r.category]);
 for(const r of i.index?.datasets||[])add('Dataset',r.id,r.label||r.id,[r.provider,r.status,r.unit,r.records==null?'':r.records+' records'].filter(Boolean).join(' · '),r.path==='data/free-research.json'?'terminal.html?research=official':'terminal.html',[r.id,r.license,r.frequency]);
 for(const r of i.catalog?.datasets||[])add('Product',r.id,r.title,[r.status,r.category,r.accessPolicy].join(' · '),'research.html',[r.id,r.description]);
 for(const r of i.routes?.routes||[])add('Freight route',r.code,r.name,[r.code,r.vessel,r.unit,'Definition only'].join(' · '),'shipping.html',[r.code,r.category]);
 return [...m.values()];
}
function search(rows,q,kind='all'){
 const p=norm(q).slice(0,180),words=p.split(/\s+/).filter(Boolean);if(!words.length)return [];
 return rows.filter(r=>kind==='all'||r.kind===kind).flatMap(r=>{const title=norm(r.title),id=norm(r.id),hay=norm([r.title,r.id,r.detail,r.terms].join(' '));if(!words.every(w=>hay.includes(w)))return [];return [{r,rank:id===p?0:title===p?1:id.startsWith(p)?2:title.startsWith(p)?3:title.includes(p)?4:5}]}).sort((a,b)=>a.rank-b.rank||Number(b.r.kind==='Company')-Number(a.r.kind==='Company')||a.r.title.localeCompare(b.r.title)).map(x=>x.r);
}
const sources={watchlist:'watchlist.json',issuers:'data/issuer-identities.json',candidates:'data/registered-source-status.json',directory:'data/instrument-directory.json',news:'data/news-archive.json',index:'data/research-index.json',catalog:'data/research-product-catalog.json',routes:'data/freight-routes.json'};
async function mount(host){
 host.innerHTML='<form class="gs-controls"><label>Search <input type="search" name="q" maxlength="180" placeholder="Company, FIGI, ticker, news or dataset"></label><label>Category <select name="kind"><option value="all">All categories</option>'+['Company','Instrument','News','Dataset','Product','Freight route'].map(x=>'<option>'+x+'</option>').join('')+'</select></label><button type="submit">Search</button></form><p role="status" data-status>Loading public indexes…</p><div data-results></div><div class="gs-pages"><button type="button" data-prev>Previous</button><span data-page></span><button type="button" data-next>Next</button></div>';
 const form=host.querySelector('form'),q=form.elements.namedItem('q'),kind=form.elements.namedItem('kind'),status=host.querySelector('[data-status]'),out=host.querySelector('[data-results]'),prev=host.querySelector('[data-prev]'),next=host.querySelector('[data-next]'),label=host.querySelector('[data-page]');let rows=[],failed=[],page=0,ready=false;
 const params=new URLSearchParams(location.search);q.value=(params.get('q')||'').slice(0,180);if([...kind.options].some(x=>x.value===params.get('kind')))kind.value=params.get('kind');
 function draw(reset=false){if(!ready)return;if(reset)page=0;const r=search(rows,q.value,kind.value),size=20;page=Math.min(page,Math.max(0,Math.ceil(r.length/size)-1));status.textContent=(q.value.trim()?r.length+' matching records':'Enter a search term')+' · '+rows.length+' indexed references'+(failed.length?' · unavailable: '+failed.join(', '):'');out.innerHTML=r.slice(page*size,(page+1)*size).map(x=>'<article class="gs-result"><small>'+E(x.kind)+'</small><h3><a href="'+E(x.href)+'"'+(x.kind==='News'?' target="_blank" rel="noopener noreferrer"':'')+'>'+E(x.title)+' ↗</a></h3><p>'+E(x.detail)+'</p></article>').join('');label.textContent=r.length?(page*size+1)+'–'+Math.min((page+1)*size,r.length)+' of '+r.length:'No results';prev.disabled=page===0;next.disabled=(page+1)*size>=r.length;}
 form.addEventListener('submit',e=>{e.preventDefault();history.replaceState(null,'','?'+new URLSearchParams({q:q.value,kind:kind.value}));draw(true)});q.addEventListener('input',()=>draw(true));kind.addEventListener('change',()=>draw(true));prev.onclick=()=>{page--;draw()};next.onclick=()=>{page++;draw()};
 const entries=await Promise.all(Object.entries(sources).map(async ([key,path])=>{try{const r=await fetch(path);if(!r.ok)throw Error('HTTP');return [key,await r.json()]}catch{failed.push(key);return [key,null]}}));rows=build(Object.fromEntries(entries));ready=true;draw(true);
}
const api={build,search,norm};if(typeof module==='object'&&module.exports)module.exports=api;else{global.StockwatchGlobalSearch=api;const host=document.getElementById('globalSearch');if(host)mount(host)}
})(typeof window!=='undefined'?window:{});
