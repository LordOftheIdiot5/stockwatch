(()=>{'use strict';
const $=id=>document.getElementById(id),page=document.body.dataset.page;
const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const N=(v,d=2)=>v==null||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('en-GB',{minimumFractionDigits:0,maximumFractionDigits:d});
const P=v=>v==null||!Number.isFinite(Number(v))?'—':(Number(v)>0?'+':'')+Number(v).toFixed(2)+'%';
const sign=v=>!Number.isFinite(Number(v))||v==null?'sw-neutral':Number(v)>0?'sw-up':Number(v)<0?'sw-down':'sw-neutral';
const link=v=>{try{const u=new URL(v,location.href);return u.protocol==='https:'?u.href:''}catch{return ''}};
const fmtDate=x=>{let d=new Date(x);return !Number.isFinite(d.getTime())?'Unknown':new Intl.DateTimeFormat('en-GB',{timeZone:'UTC',day:'numeric',month:'short',year:'numeric'}).format(d)};
const timeAge=x=>{let n=(Date.now()-Date.parse(x))/3600000;if(!Number.isFinite(n))return 'Unknown';if(n<0)return 'Clock mismatch';return n<2?`${Math.max(1,Math.floor(n*60))} min ago`:n<48?`${Math.floor(n)} hours ago`:`${Math.floor(n/24)} days ago`};
const get=async path=>{let r=await fetch(path+(path.includes('?')?'&':'?')+'v='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error(`HTTP ${r.status}: ${path}`);return r.json()};
const state={signals:null,context:null,watchlist:[],routes:[],health:null,archive:null,fundamentals:{},history:new Map(),missingHistory:new Set(),selection:null,observations:null,identities:null,issuers:null,onboarding:null,researchTargets:null,researchCoverage:null,intelligence:null,referenceDirectory:null,expansion:null,licensedPrices:null};
const companies=()=>{const live=new Map((state.signals?.companies||[]).map(x=>[x.ticker,x]));return state.watchlist.map(w=>live.has(w.ticker)?{...w,...live.get(w.ticker)}:{...w,unavailable:true})};
const priced=()=>companies().filter(x=>!x.unavailable&&Number.isFinite(x.close));
const top=(a,n)=>a.slice(0,n);
const chart=(points,width=88,height=26)=>{if(!Array.isArray(points)||points.length<2)return '<span class="sw-meta">—</span>';const values=points.map(x=>+x).filter(Number.isFinite);if(values.length<2)return '—';const min=Math.min(...values),max=Math.max(...values),span=max-min||1;const path=values.map((v,i)=>`${i?'L':'M'} ${(i/(values.length-1)*width).toFixed(2)} ${(height-2-(v-min)/span*(height-4)).toFixed(2)}`).join(' ');const color=values.at(-1)>=values[0]?'var(--sw-green)':'var(--sw-red)';return `<svg class="sw-spark" viewBox="0 0 ${width} ${height}" aria-hidden="true" preserveAspectRatio="none"><path d="${path}" fill="none" stroke="${color}" stroke-width="1.8" stroke-linejoin="round"/></svg>`};
function stat(label,value,desc,cls=''){return `<article class="sw-card sw-stat"><div class="sw-stat-label">${E(label)}</div><div class="sw-stat-num ${cls}">${E(value)}</div><div class="sw-stat-sub">${E(desc)}</div></article>`}
function panelHeader(title,linkText='',url='',meta=''){return `<div class="sw-panel-hd"><div><h2>${E(title)}</h2>${meta?`<small>${E(meta)}</small>`:''}</div>${url?`<a class="sw-textlink" href="${url}">${E(linkText)} ↗</a>`:''}</div>`}
function storyData(){const source=state.archive?.items||[];if(source.length)return source;const out=[];for(const c of state.signals?.companies||[])for(const s of c.stories||[])if(['news','disclosure'].includes(s.kind))out.push({...s,ticker:c.ticker,name:c.name,sector:c.sector,type:s.kind});return out.sort((a,b)=>Date.parse(b.published)-Date.parse(a.published))}
function storyHead(s){const original=String(s.headline||'');const translated=String(s.english||'');const yr=(original.match(/\b20\d\d\b/g)||[]);const ty=(translated.match(/\b20\d\d\b/g)||[]);const safe=translated&&(!yr.length||!ty.length||yr.some(y=>ty.includes(y)));return safe?translated:original||translated||'Company update'}
function storyBrief(s){const u=link(s.url);const txt=E(storyHead(s));return `<div class="sw-brief"><div class="sw-brief-kicker"><span class="sw-tag ${s.type==='disclosure'||s.kind==='disclosure'?'mint':''}">${s.type==='disclosure'||s.kind==='disclosure'?'Regulatory / filing':'News'}</span><span>${E(s.name||s.ticker||'')}</span></div><h4>${u?`<a href="${E(u)}" target="_blank" rel="noopener noreferrer">${txt}</a>`:txt}</h4><p>${E(s.publisher||'Source')} · ${fmtDate(s.published)}</p></div>`}
function moversHtml(arr){return arr.map(c=>`<a class="sw-listline" href="stocks.html?ticker=${encodeURIComponent(c.ticker)}"><span class="sw-company">${E(c.name)}<small>${E(c.ticker)}</small></span>${chart(c.spark)}<span class="sw-price">${N(c.close,3)}<small>${E(c.currency||'')}</small></span><span class="sw-change ${sign(c.changePct)}">${P(c.changePct)}</span></a>`).join('')||'<div class="sw-empty">No priced listings available.</div>'}
function tape(){const c=state.context;if(!c?.commodities?.length)return;const names=['Gold','Brent crude','Natural gas','Copper'];const items=names.map(name=>c.commodities.find(x=>x.name===name)).filter(Boolean);$('swTape').innerHTML=`<span>MARKET PULSE</span><div class="sw-tape-content">${items.map(x=>`<span>${E(x.name)} <b>${N(x.last,2)}</b> <i class="${sign(x.changePct)}">${P(x.changePct)}</i></span>`).join('')}</div>`}
function sectorSummaries(all){const groups=new Map();for(const c of all){let k=c.sector||'Other';if(!groups.has(k))groups.set(k,[]);groups.get(k).push(c.changePct||0)}let a=[...groups].map(([name,arr])=>{let d=[...arr].sort((x,y)=>x-y),mid=Math.floor(d.length/2);return {name,median:d.length%2?d[mid]:(d[mid-1]+d[mid])/2,n:arr.length}}).sort((x,y)=>Math.abs(y.median)-Math.abs(x.median)).slice(0,6);const max=Math.max(1,...a.map(x=>Math.abs(x.median)));return a.map(x=>`<a class="sw-sector-item" href="stocks.html?sector=${encodeURIComponent(x.name)}"><span><b>${E(x.name)}</b><small>${x.n} stocks</small></span><span class="sw-sector-bar"><i style="width:${Math.max(3,Math.abs(x.median)/max*100)}%;background:${x.median<0?'var(--sw-red)':'var(--sw-green)'}"></i></span><strong class="${sign(x.median)}">${P(x.median)}</strong></a>`).join('')}
/* V21: market workspace using observed values only. */
function marketHeatData(all,group='all'){
 return all.filter(x=>x&&!x.unavailable&&Number.isFinite(x.close)&&Number.isFinite(x.changePct)&&(group==='all'||x.sector===group));
}
function workspaceHeatmap(all,group='all'){
 const groups=new Map();for(const x of marketHeatData(all,group)){const label=x.sector||'Other';if(!groups.has(label))groups.set(label,[]);groups.get(label).push(x)}
 if(!groups.size)return '<div class="sw-empty">No observed price changes in this selection.</div>';
 return [...groups].sort((a,b)=>b[1].length-a[1].length||a[0].localeCompare(b[0])).map(([label,items])=>'<section class="sw-heat-sector"><h3>'+E(label)+' <small>'+items.length+'</small></h3><div class="sw-heat-cells">'+items.slice().sort((a,b)=>Math.abs(b.changePct)-Math.abs(a.changePct)).map(x=>'<a class="sw-heat-cell '+(x.changePct>0?'positive':x.changePct<0?'negative':'flat')+'" data-strength="'+Math.min(5,Math.ceil(Math.abs(x.changePct)))+'" href="stocks.html?ticker='+encodeURIComponent(x.ticker)+'" title="'+E(x.name+' · '+P(x.changePct))+'" aria-label="'+E(x.name+', '+P(x.changePct))+'"><strong>'+E(x.ticker)+'</strong><span>'+E(P(x.changePct))+'</span></a>').join('')+'</div></section>').join('');
}
/* V28: reference coverage does not become market data. */
function coverageHeatRows(all,group='all',coverage='all'){
 return all.filter(x=>(group==='all'||x.sector===group)&&(coverage==='all'||(coverage==='observed'?marketHeatData([x]).length:!marketHeatData([x]).length)));
}
function coverageHeatmap(rows){
 const market=workspaceHeatmap(rows),missing=rows.filter(x=>!marketHeatData([x]).length);
 if(!missing.length)return market;
 const groups=new Map();
 for(const x of missing){const s=x.sector||'Other';if(!groups.has(s))groups.set(s,[]);groups.get(s).push(x)}
 return (marketHeatData(rows).length?market:'')+[...groups].map(([label,items])=>'<section class="sw-heat-sector sw-heat-missing"><h3>'+E(label)+' · no change data <small>'+items.length+'</small></h3><div class="sw-heat-cells">'+items.map(x=>'<a class="sw-heat-cell no-data" href="'+(x.registryOnly?'directory.html?q='+encodeURIComponent(x.figi):x.referenceOnly?'research.html?instrument='+encodeURIComponent(x.referenceId)+'#targetDetail':'company.html?ticker='+encodeURIComponent(x.ticker))+'" title="'+E(x.name+' · no observed change')+'"><strong>'+E(x.symbol||x.ticker)+'</strong><span>—</span></a>').join('')+'</div></section>').join('');
}
function referenceCatalogRows(data){
 const seen=new Set(),out=[];
 for(const x of data?.records||[]){
  if(!x||typeof x.figi!=='string'||!/^[A-Z0-9]{12}$/.test(x.figi)||!x.mic||!x.name||!x.ticker)continue;
  const id=x.mic+':'+x.figi;if(seen.has(id))continue;seen.add(id);
  out.push({ticker:'registry:'+id,name:x.name,symbol:x.ticker,exchange:x.venue||x.mic,mic:x.mic,figi:x.figi,sector:'Reference / unclassified',referenceOnly:true,registryOnly:true,unavailable:true});
 }
 return out;
}
function screenMetric(value,minimum,absolute=false){
 if(minimum===''||minimum==null)return true;
 const n=Number(minimum);return Number.isFinite(n)&&n>=0&&typeof value==='number'&&Number.isFinite(value)&&(absolute?Math.abs(value):value)>=n;
}
function screenFinancialRows(rows,filters){
 return rows.filter(r=>{
  if(filters.move!==''&&(r.unavailable||!screenMetric(r.changePct,filters.move,true)))return false;
  if(filters.volume!==''&&(r.unavailable||r.thin||!screenMetric(r.rvol,filters.volume)))return false;
  if(filters.volatility!==''&&(r.referenceOnly||!screenMetric(r.annualVolPct,filters.volatility)))return false;
  if(filters.signal&&(r.unavailable||!(Number.isFinite(r.excessSigma)&&Math.abs(r.excessSigma)>=2||!r.thin&&Number.isFinite(r.rvol)&&r.rvol>=2.5)))return false;
  return true;
 });
}
function overview(){
 const listed=companies(),universe=directoryRows(),references=universe.filter(x=>x.referenceOnly),valid=priced(),observed=marketHeatData(valid),news=storyData();
 const up=observed.filter(c=>c.changePct>0).length,down=observed.filter(c=>c.changePct<0).length,flat=observed.length-up-down;
 const ranked=observed.slice().sort((a,b)=>Math.abs(b.changePct)-Math.abs(a.changePct));
 const active=valid.filter(c=>Math.abs(c.excessSigma||0)>=2||(c.rvol>=2.5&&!c.thin)).length;
 const latest=news.slice().sort((a,b)=>Date.parse(b.published)-Date.parse(a.published)).slice(0,4);
 const sectors=[...new Set(universe.map(x=>x.sector).filter(Boolean))].sort();
 const venueCount=new Set(universe.map(x=>x.exchange).filter(Boolean)).size;
 const pct=n=>observed.length?100*n/observed.length:0;
 const modules=[
 ['equities','Stocks & sectors','Search listings, compare signals and build a watchlist.','stocks.html','▥'],
 ['shipping','Shipping & freight','Global maritime routes and independent voyage models.','shipping.html','⚓'],
 ['energy','Commodities','Energy, metals and macro indicators.','commodities.html','◈'],
 ['spreads','Share-class spreads','Compare A/B premiums and relative value.','spreads.html','⇌'],
 ['events','Earnings calendar','Upcoming company events and disclosures.','calendar.html','▦'],
 ['news','News & filings','Read chronological source-linked announcements.','news.html','▤'],
 ['compare','Compare stocks','Compare companies side by side.','compare.html','⇄'],
 ['shorts','Short positions','Explore disclosed short positions.','shorts.html','↘'],
 ['research','Data health','Source coverage, timestamps and limitations.','health.html','◉']
 ];
 const pulse=(state.context?.commodities||[]).filter(x=>['Gold','Copper','Brent crude','Natural gas'].includes(x.name)).map(x=>'<a class="sw-ws-pulse" href="commodities.html"><span>'+E(x.name)+'</span><strong>'+N(x.last,3)+' <small>'+E(x.unit||'')+'</small></strong><b class="'+sign(x.changePct)+'">'+P(x.changePct)+'</b></a>').join('');
 $('v4app').innerHTML=
 '<section class="sw-ws-hero"><div class="sw-ws-intro"><span class="sw-ws-eyebrow">STOCKWATCH / MARKET WORKSPACE</span><h1>See the market.<br><em>Find the signal.</em></h1><p>European equities, filings, shipping and macro intelligence in a connected research workspace.</p><div class="sw-ws-actions"><a class="sw-primary" href="stocks.html">Explore companies ↗</a><a class="sw-soft-btn" href="news.html">Latest disclosures</a></div></div><div class="sw-ws-hero-visual"><span class="sw-ws-eyebrow">COVERAGE AT A GLANCE</span><div class="sw-ws-cover-number">'+N(universe.length,0)+' <small>research listings</small></div><div class="sw-ws-coverage"><div><span>Price-monitored listings</span><b>'+listed.length+'</b></div><div><span>Licensed EOD reference series</span><b>'+licensedReferenceCount(universe)+'</b></div><div><span>Reference listings without prices</span><b>'+(references.length-licensedReferenceCount(universe))+'</b></div><div><span>Trading venues (research universe)</span><b>'+venueCount+'</b></div><div><span>Observed prices</span><b>'+valid.length+'</b></div></div><div class="sw-ws-caption"><a class="sw-textlink" href="stocks.html?universe=registry">'+(state.referenceDirectory?N(state.referenceDirectory.records?.length||0,0)+' OpenFIGI venue reference records':'OpenFIGI reference directory')+' ↗</a><small class="sw-registry-note">Separate reference catalog; may overlap research listings.</small><a class="sw-textlink" href="price-history.html">Licensed price coverage &amp; historical series ↗</a></div><div class="sw-ws-caption">Latest scan: '+E(state.signals?.generated?fmtDate(state.signals.generated)+' · '+timeAge(state.signals.generated):'Unavailable')+'</div></div></section>'+
 '<div class="sw-section-row"><h2>Market pulse</h2><small>Latest observed data · not live exchange quotes</small></div><div class="sw-ws-pulse-grid">'+(pulse||'<div class="sw-note">Market context unavailable.</div>')+'</div>'+
 '<div class="sw-ws-metrics">'+stat('Watchlist median',P(state.signals?.marketPct),'Not an exchange index',sign(state.signals?.marketPct))+stat('Relative signals',N(active,0),'Unusual price or volume activity')+'<article class="sw-card sw-stat sw-ws-breadth"><div class="sw-stat-label">Market breadth</div><div class="sw-ws-breadth-values"><strong class="sw-up">'+up+' up</strong><strong class="sw-down">'+down+' down</strong><span>'+flat+' unchanged</span></div><div class="sw-ws-breadth-bar" aria-label="'+up+' advancing, '+down+' declining, '+flat+' unchanged"><i style="width:'+pct(up)+'%;background:var(--sw-green)"></i><i style="width:'+pct(flat)+'%;background:var(--sw-dim)"></i><i style="width:'+pct(down)+'%;background:var(--sw-red)"></i></div><small>'+observed.length+' listings with observed changes</small></article></div>'+
 '<section class="sw-panel sw-ws-heatmap">'+panelHeader('Market map','Open stock screener','stocks.html','Equal-size tiles · observed 1D changes and reference coverage')+'<div class="sw-panel-pad"><div class="sw-ws-heat-toolbar"><label for="workspaceSector">Sector</label><select id="workspaceSector"><option value="all">All sectors</option>'+sectors.map(s=>'<option value="'+E(s)+'">'+E(s)+'</option>').join('')+'</select><label for="workspaceCoverage">Coverage</label><select id="workspaceCoverage"><option value="all">All research listings</option><option value="observed" selected>Observed changes only</option><option value="missing">No observed change</option></select><span id="workspaceHeatCount" aria-live="polite"></span><div class="sw-ws-legend"><span class="sw-down">− Loss</span><span>0% Flat</span><span class="sw-up">+ Gain</span><span>— No data</span></div></div><div id="workspaceHeatmap" class="sw-heatmap-grid"></div><p class="sw-meta">Tiles are equally weighted. Dashed neutral tiles lack observed price changes and are not treated as zero returns. Market breadth and sector performance use observed changes only.</p></div></section>'+
 '<div class="sw-two-col"><section class="sw-panel">'+panelHeader('Biggest observed moves','All listings','stocks.html','Ranked by absolute change')+'<div>'+moversHtml(top(ranked,7))+'</div></section><section class="sw-panel">'+panelHeader('Company intelligence','News & filings','news.html','Source-linked announcements and news')+'<div>'+(latest.length?latest.map(storyBrief).join(''):'<div class="sw-empty">No news currently available.</div>')+'</div></section></div>'+
 '<div class="sw-section-row"><h2>Sector performance</h2><a href="stocks.html" class="sw-textlink">Explore sectors ↗</a></div><div class="sw-sector-grid">'+sectorSummaries(observed)+'</div>'+
 '<div class="sw-section-row"><h2>Research workspace</h2><small>Specialized tools, common data principles</small></div><div class="sw-ws-modules">'+modules.map(([kind,title,desc,url,ic])=>'<a class="sw-card sw-ws-module" href="'+url+'"><div class="sw-ws-module-art '+kind+'" aria-hidden="true"><span>'+ic+'</span><i></i><i></i><i></i></div><div class="sw-ws-module-text"><h3>'+E(title)+' <span>↗</span></h3><p>'+E(desc)+'</p></div></a>').join('')+'</div>'+
 '<section class="sw-panel sw-ws-trust">'+panelHeader('Trust & data infrastructure','Data health','health.html','Source provenance, freshness and coverage')+'<div class="sw-panel-pad"><div><b>Stockwatch</b><p>Independent market research. Observations can be delayed; missing data is not invented.</p><a class="sw-textlink" href="intelligence.html">Explore connected intelligence ↗</a> <a class="sw-textlink" href="research.html">OpenFIGI integration &amp; historical evidence ↗</a></div><div><b>Leivro</b><p>Our intended central dataset and API platform. Shared infrastructure is being developed.</p><a class="sw-textlink" href="https://leivro.com/">Explore Leivro ↗</a></div></div></section>';
 document.body.classList.add('sw-workspace-ready');
 const select=$('workspaceSector'),coverage=$('workspaceCoverage');const draw=()=>{const rows=coverageHeatRows(universe,select.value,coverage.value);$('workspaceHeatmap').innerHTML=coverageHeatmap(rows);$('workspaceHeatCount').textContent=rows.length+' listings · '+marketHeatData(rows).length+' with changes'};select.addEventListener('change',draw);coverage.addEventListener('change',draw);draw();
}
function instrumentIdentityPanel(t){
 const candidates=(state.identities?.figiCandidates||[]).filter(x=>x.ticker===t);
 const issuers=(state.issuers?.entities||[]).filter(x=>x.ticker===t);
 const one=issuers.length===1?issuers[0]:null,candidate=candidates.length===1?candidates[0]:null;
 const fmt=(label,value)=>'<div><small>'+E(label)+'</small><b>'+E(value||'Unavailable')+'</b></div>';
 return '<section class="sw-identity-panel"><div class="sw-section-row"><h2>Instrument identity</h2><a class="sw-textlink" href="https://www.openfigi.com/" target="_blank" rel="noopener noreferrer">OpenFIGI ↗</a></div><p class="sw-meta">Listing-level reference data; FIGI identifiers are candidates unless independently verified. No issuer relationship is inferred from ticker similarity. <a class="sw-textlink" href="research.html">OpenFIGI mapping methodology &amp; historical coverage ↗</a></p><div class="sw-identity-grid">'+fmt('Listing ticker',t)+fmt('ISIN (issuer directory)',one?.isin)+fmt('FIGI candidate',candidate?.figi)+fmt('Share-class FIGI candidate',candidate?.shareClassFIGI)+fmt('Composite FIGI candidate',candidate?.compositeFIGI)+fmt('Mapping status',candidates.length>1?'Multiple candidates — unresolved':candidate?'Candidate — not verified':'Not mapped')+'</div></section>';
}
function sectorChips(items,active,call){return `<div class="sw-filter-row">${['All',...items].map(s=>`<button type="button" data-${call}="${E(s)}" class="${s===active?'active':''}">${E(s)}</button>`).join('')}</div>`}
function renderFacts(c){const f=state.fundamentals?.[c.ticker],m=f?.metrics||{};const keys=[['Market cap','marketCap'],['Revenue','revenue'],['Net income','netIncome'],['EPS','eps'],['P/E','pe'],['P/B','pb'],['Dividend yield','dividendYield']];const present=keys.filter(([label,k])=>Number.isFinite(m[k]));if(!present.length)return '<div class="sw-note">Verified earnings and valuation metrics are not yet loaded for this listing. Stockwatch does not estimate or invent missing fundamentals.</div>';return `<div class="sw-section-row"><h2>Verified financial fundamentals</h2><a class="sw-textlink" href="${E(link(f.sourceUrl))}" target="_blank" rel="noopener noreferrer">Original filing ↗</a></div><div class="sw-stat-mini">${present.map(([label,k])=>`<div><small>${E(label)}</small><b>${N(m[k],k==='revenue'||k==='marketCap'||k==='netIncome'?0:2)}${k==='dividendYield'?'%':''}</b></div>`).join('')}</div><p class="sw-meta">${E(f.period||'')} · ${E(f.asOf||'')} · ${E(f.currency||'')} · ${E(f.sourceName||'Original issuer source')}</p>`};
/* V25b: reference listings remain independent of the price scanner. */
function researchUniverse(monitored,targets,coverage){
 const venues={XOSL:'Oslo',XSTO:'Stockholm',XCSE:'Copenhagen',XHEL:'Helsinki',XETR:'XETRA',XPAR:'Paris',XLON:'London',XSWX:'SIX Swiss',XAMS:'Amsterdam'};
 const suffix={Oslo:'.OL',Stockholm:'.ST',Copenhagen:'.CO',Helsinki:'.HE',XETRA:'.DE',Paris:'.PA',London:'.L','SIX Swiss':'.SW',Amsterdam:'.AS'};
 const norm=s=>String(s||'').toUpperCase().replace(/[\s./-]+/g,'');
 const keys=new Set(monitored.map(r=>{const s=suffix[r.exchange];return s&&r.ticker.endsWith(s)?r.exchange+':'+norm(r.ticker.slice(0,-s.length)):null}).filter(Boolean));
 const byId=new Map((coverage?.records||[]).map(r=>[r.id,r]));
 const used=new Set(),extra=[];
 for(const t of targets?.targets||[]){
  if(!t.id||!t.symbol||!t.name||!venues[t.mic]||used.has(t.id))continue;
  used.add(t.id);
  if(keys.has(venues[t.mic]+':'+norm(t.symbol)))continue;
  const evidence=byId.get(t.id);
  const match=evidence&&evidence.mic===t.mic&&evidence.symbol===t.symbol?evidence:null;
  extra.push({ticker:'ref:'+t.id,name:t.name,exchange:venues[t.mic],sector:t.sector||'Research / unclassified',referenceOnly:true,unavailable:true,symbol:t.symbol,mic:t.mic,isin:t.isin,referenceId:t.id,mappingStatus:match?.mappingStatus||'awaiting_mapping',figi:match?.currentCandidate?.figi||null});
 }
 return [...monitored,...extra];
}
/* V26: typed, auditable research relationships. No inferred ownership or causal edges. */
function intelligenceGraph(listings,rules,identities){
 const nodes=new Map(),edges=new Map();
 const node=(id,type,label,extra={})=>{if(!nodes.has(id))nodes.set(id,{id,type,label,...extra});return id};
 const edge=(from,to,type,evidence)=>edges.set(JSON.stringify([from,to,type]),{from,to,type,evidence});
 const config=rules||{};
 const datasets=new Map((config.datasets||[]).map(x=>[x.id,x]));
 const candidates=new Map();
 for(const x of identities?.figiCandidates||[]){if(!candidates.has(x.ticker))candidates.set(x.ticker,[]);candidates.get(x.ticker).push(x)}
 for(const r of listings){
  const id=node('listing:'+r.ticker,'listing',r.name,{ticker:r.ticker,referenceOnly:!!r.referenceOnly,href:r.registryOnly?'directory.html?q='+encodeURIComponent(r.figi):r.referenceOnly?'research.html?instrument='+encodeURIComponent(r.referenceId)+'#targetDetail':'company.html?ticker='+encodeURIComponent(r.ticker)});
  const sector=r.sector||'Unclassified',s=node('sector:'+sector,'sector',sector,{href:'stocks.html?sector='+encodeURIComponent(sector)});
  if(!r.registryOnly)edge(id,s,'classified_as','Stockwatch editorial sector classification');
  if(r.exchange){const v=node('venue:'+r.exchange,'venue',r.exchange);edge(id,v,'directory_venue','Listing directory metadata; not issuer domicile')}
  const options=candidates.get(r.ticker)||[];
  const figi=r.referenceOnly?(r.mappingStatus==='candidate'?r.figi:null):(options.length===1?options[0].figi:null);
  if(typeof figi==='string'&&/^[A-Z0-9]{12}$/.test(figi)){const m=node('figi:'+figi,'identifier',figi,{href:'research.html'});edge(id,m,'candidate_identifier','OpenFIGI mapping candidate; not independently verified')}
  for(const rule of config.rules||[]){
   if(!rule.sectors?.includes(sector))continue;
   for(const did of rule.datasets||[]){const d=datasets.get(did);if(!d)continue;
    const target=node('dataset:'+did,'dataset',d.label,{href:d.href,source:d.source,file:d.file,key:d.key});
    edge(s,target,'research_context',rule.reason);
   }
  }
 }
 return {schemaVersion:1,nodes:[...nodes.values()],edges:[...edges.values()]};
}
function graphNeighborhood(graph,ticker){
 const id='listing:'+ticker,center=graph.nodes.find(n=>n.id===id);if(!center)return null;
 const direct=graph.edges.filter(e=>e.from===id),sector=direct.find(e=>e.type==='classified_as')?.to;
 const nodeById=new Map(graph.nodes.map(n=>[n.id,n]));
 const context=graph.edges.filter(e=>e.from===sector&&e.type==='research_context').map(e=>({...nodeById.get(e.to),evidence:e.evidence}));
 const peers=graph.edges.filter(e=>e.to===sector&&e.type==='classified_as'&&e.from!==id).map(e=>nodeById.get(e.from)).filter(Boolean).sort((a,b)=>a.label.localeCompare(b.label));
 return {center,direct:direct.map(e=>({...nodeById.get(e.to),evidence:e.evidence,relation:e.type})),context,peers};
}
function activeIntelligenceGraph(){return intelligenceGraph(directoryRows(),state.intelligence,state.identities)}
function intelligencePanel(c){
 const n=graphNeighborhood(activeIntelligenceGraph(),c.ticker);if(!n)return '';
 return '<section class="sw-intel-summary"><div class="sw-section-row"><h2>Connected intelligence</h2><a class="sw-textlink" href="intelligence.html?ticker='+encodeURIComponent(c.ticker)+'">Explore graph ↗</a></div><p class="sw-meta">Sector-based research context, not proven exposure, correlation or causal relationships.</p><div class="sw-intel-mini">'+(n.context.map(x=>'<a class="sw-peer" href="'+E(x.href)+'"><small>'+E(x.source)+'</small><strong>'+E(x.label)+'</strong><small>Editorial context</small></a>').join('')||'<p class="sw-meta">No curated context links for this sector yet.</p>')+'</div></section>';
}
async function intelligencePage(){
 const root=$('v4app'),graph=activeIntelligenceGraph(),list=graph.nodes.filter(n=>n.type==='listing').sort((a,b)=>a.label.localeCompare(b.label));
 if(!list.length){root.innerHTML='<p class="sw-note">No instrument directory available.</p>';return}
 const p=new URLSearchParams(location.search),selected=list.find(n=>n.ticker===p.get('ticker'))?.ticker||list.find(n=>n.ticker==='FRO.OL')?.ticker||list[0].ticker;
 root.innerHTML='<div class="sw-grid4">'+stat('Listings',N(list.length,0),'Research universe')+stat('Graph nodes',N(graph.nodes.length,0),'Typed reference nodes')+stat('Relationships',N(graph.edges.length,0),'Evidence and context links')+stat('Context series',N(graph.nodes.filter(x=>x.type==='dataset').length,0),'Existing research datasets')+'</div><section class="sw-panel sw-intel-panel">'+panelHeader('Explore connected intelligence','Methodology','research.html','Evidence and editorial context are separate relationship types')+'<div class="sw-panel-pad"><div class="sw-controls"><input id="intelSearch" type="search" aria-label="Filter listings" placeholder="Find a company or ticker"><select id="intelListing" aria-label="Select listing"></select></div><div id="intelMap"></div><div id="intelData"></div><div id="intelPeers"></div></div></section>';
 const search=$('intelSearch'),select=$('intelListing');let current=selected;
 function options(){const q=search.value.trim().toLowerCase(),rows=list.filter(n=>(n.label+' '+n.ticker).toLowerCase().includes(q));select.innerHTML=rows.map(n=>'<option value="'+E(n.ticker)+'">'+E(n.label+' · '+n.ticker.replace(/^ref:/,''))+'</option>').join('');if(rows.some(x=>x.ticker===current))select.value=current;else if(rows.length)current=rows[0].ticker;return rows.length}
 let generation=0;
 async function draw(){
  const version=++generation,n=graphNeighborhood(graph,current);
  if(!n||!select.options.length){$('intelMap').innerHTML='<p class="sw-note">No matching listings.</p>';$('intelData').textContent='';$('intelPeers').textContent='';return}
  const branch=(x)=>'<div class="sw-intel-node"><small>'+E(x.type==='identifier'?'Unverified candidate':x.type==='sector'?'Editorial sector':'Directory venue')+'</small>'+(x.href?'<a href="'+E(x.href)+'"><strong>'+E(x.label)+'</strong></a>':'<strong>'+E(x.label)+'</strong>')+'<span>'+E(x.evidence)+'</span></div>';
  $('intelMap').innerHTML='<div class="sw-intel-map"><div class="sw-intel-center"><small>'+E(n.center.referenceOnly?'REFERENCE ONLY':'MONITORED LISTING')+'</small><a href="'+E(n.center.href)+'"><strong>'+E(n.center.label)+'</strong></a><span>Selected instrument record</span></div><div class="sw-intel-connector" aria-hidden="true"></div><div class="sw-intel-branches">'+n.direct.map(branch).join('')+'</div></div><p class="sw-meta">Listed venue does not identify company domicile. Shared classifications and identifier candidates do not establish corporate ownership or verified economic links.</p>';
  $('intelPeers').innerHTML='<div class="sw-section-row"><h2>Other listings in this sector</h2><small>'+n.peers.length+' directory peers</small></div><div class="sw-intel-mini">'+(n.peers.slice(0,12).map(x=>'<button class="sw-peer sw-intel-peer" type="button" data-intel-peer="'+E(x.ticker)+'"><strong>'+E(x.label)+'</strong><small>'+E(x.referenceOnly?'Reference only':'Monitored listing')+'</small></button>').join('')||'<p class="sw-meta">No other listings in this classification.</p>')+'</div>';
  $('intelData').innerHTML='<h2>Sector research context</h2><p class="sw-meta">Editorial links only. These are not measured exposures or forecasts.</p><div class="sw-intel-mini" id="intelContextCards">'+(n.context.map(x=>'<div class="sw-peer"><small>'+E(x.source)+'</small><a href="'+E(x.href)+'"><strong>'+E(x.label)+' ↗</strong></a><span>'+E(x.evidence)+'</span><small>Checking published coverage…</small></div>').join('')||'<p class="sw-meta">No curated contextual series.</p>')+'</div>';
  const result=await Promise.all(n.context.map(async x=>{try{const d=await get(x.file);if(x.key){const s=(d.series||[]).find(y=>y.key===x.key);return s?{status:'Published series',period:s.period,unit:s.unit,sourceUrl:s.sourceUrl,license:s.license}:null}return Array.isArray(d.series)&&d.series.length?{status:d.series.length+' published series',sourceUrl:d.sourceUrl,license:d.license}:null}catch{return null}}));
  if(version!==generation)return;
  const cards=$('intelContextCards').children;
  result.forEach((r,i)=>{const card=cards[i];if(!card)return;const foot=card.lastElementChild;foot.textContent=r?[r.status,r.period,r.unit].filter(Boolean).join(' · '):'No published observations confirmed';if(r?.license){const note=document.createElement('small');note.textContent=r.license;card.appendChild(note)}if(r?.sourceUrl&&/^https:\/\//.test(r.sourceUrl)){const a=document.createElement('a');a.className='sw-textlink';a.href=r.sourceUrl;a.target='_blank';a.rel='noopener noreferrer';a.textContent='Original source ↗';card.appendChild(a)}});
 }
 search.addEventListener('input',()=>{options();draw()});select.addEventListener('change',()=>{current=select.value;draw()});
 root.addEventListener('click',e=>{const b=e.target.closest('[data-intel-peer]');if(b){current=b.dataset.intelPeer;search.value='';options();draw()}});
 options();await draw();
}
/* V29b: licensed EOD coverage is separate from the legacy scanner. */
function licensedReferenceRows(index,universe){
 const ids=new Map(universe.filter(r=>r.referenceOnly).map(r=>[r.ticker,r]));
 const valid=new Map();
 for(const p of index?.records||[]){
  if(!ids.has(p.listingId)||p.redistributionPermitted!==true||p.priceType!=='end_of_day'||!Number.isFinite(p.close)||p.close<=0||!Number.isFinite(p.changePct)||!/^\d{4}-\d{2}-\d{2}$/.test(p.lastDate||'')||!/^data\/licensed-reference-history\/[a-f0-9]{32}\.json$/.test(p.historyPath||'')||!p.source||!p.licenseReference||!p.currency)continue;
  valid.set(p.listingId,p);
 }
 return valid;
}
function licensedReferenceCount(universe){return licensedReferenceRows(state.licensedPrices,universe).size}
function licensedHistoryUrl(id){return 'price-history.html?listing='+encodeURIComponent(id)}
async function licensedPricePage(){
 const root=$('v4app'),universe=directoryRows(),prices=licensedReferenceRows(state.licensedPrices,universe);
 const requested=new URLSearchParams(location.search).get('listing');
 const row=universe.find(x=>x.ticker===requested),q=prices.get(requested);
 if(requested&&!row){root.innerHTML='<div class="sw-note">Unknown research listing. <a href="stocks.html">Open stocks directory ↗</a></div>';return}
 const linkTo=(r,p)=>'<tr><td><a class="sw-textlink" href="'+licensedHistoryUrl(r.ticker)+'">'+E(r.name)+'</a></td><td>'+E(p.currency)+' '+E(N(p.close,4))+'</td><td>'+E(p.lastDate)+'</td><td>'+E(p.source)+'</td></tr>';
 if(!requested){root.innerHTML='<div class="sw-grid4">'+stat('Licensed EOD series',prices.size,'Reference-universe histories')+stat('Research universe',universe.length,'Listings, not unique issuers')+'</div><section class="sw-panel">'+panelHeader('Licensed price coverage','Stocks directory','stocks.html','Daily closes, not live quotes')+'<div class="sw-panel-pad">'+(prices.size?'<div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Listing</th><th>Last close</th><th>Session date</th><th>Source</th></tr></thead><tbody>'+universe.filter(r=>prices.has(r.ticker)).map(r=>linkTo(r,prices.get(r.ticker))).join('')+'</tbody></table></div>':'<p>No licensed reference price series have been imported. Provider permissions and reviewed instrument mappings are required.</p>')+'</div></section>';return}
 root.innerHTML='<section class="sw-panel"><div class="sw-panel-pad"><h2>'+E(row.name)+'</h2><p class="sw-meta">'+E(row.symbol||row.ticker)+' · '+E(row.exchange||'')+' · End-of-day history</p><div id="licensedSeries"></div><p><a class="sw-textlink" href="stocks.html">All research listings ↗</a> · <a class="sw-textlink" href="research.html">Source methodology ↗</a></p></div></section>';
 const target=$('licensedSeries');
 if(!q){target.innerHTML='<div class="sw-note">Licensed daily historical prices are not connected for this listing.</div>';return}
 const d=await get(q.historyPath).catch(()=>null);
 if(!d||d.listingId!==q.listingId||d.redistributionPermitted!==true||d.priceType!=='end_of_day'||d.currency!==q.currency||d.source!==q.source||d.licenseReference!==q.licenseReference||!Array.isArray(d.bars)){target.innerHTML='<div class="sw-note">Licensed history unavailable or inconsistent.</div>';return}
 const bars=d.bars.filter(x=>Number.isFinite(x.close)&&x.close>0).map(x=>({date:x.date,value:x.close}));
 target.innerHTML='<div class="sw-history-source"><strong>'+E(q.source)+'</strong><span>'+E(q.currency)+' · '+(d.adjusted?'Adjusted':'Unadjusted')+' closes · '+E(q.lastDate)+'</span><a class="sw-textlink" href="'+E(link(d.sourceUrl))+'">Source ↗</a> <a class="sw-textlink" href="'+E(link(d.licenseReference))+'">Licence ↗</a></div>'+lineGraph(bars,{label:row.name+' · licensed EOD close',unit:q.currency})+'<p class="sw-meta">Change is between consecutive recorded closes; missing sessions are not filled. These observations are separate from the legacy scanner signals.</p>';
}
function directoryRows(){
 const base=researchUniverse(companies(),state.researchTargets,state.researchCoverage);
 return [...base,...referenceCatalogRows(state.expansion).map(x=>({...x,expandedReference:true}))];
}
function quickMatches(rows,query){
 const q=query.trim().toLowerCase();if(!q)return [];
 return rows.map(r=>{const symbol=String(r.symbol||r.ticker).toLowerCase(),name=String(r.name||'').toLowerCase(),id=String(r.figi||'').toLowerCase();return {r,score:symbol===q||id===q?0:name===q?1:symbol.startsWith(q)?2:name.startsWith(q)?3:[name,symbol,id,r.isin||''].join(' ').toLowerCase().includes(q)?4:99}}).filter(x=>x.score<99).sort((a,b)=>a.score-b.score||Number(!!a.r.referenceOnly)-Number(!!b.r.referenceOnly)||a.r.name.localeCompare(b.r.name)).slice(0,7).map(x=>x.r);
}
function wireQuickSearch(){
 const input=$('swGlobalSearch'),form=$('swSearchForm');if(!input||!form)return;
 const box=document.createElement('div');box.className='sw-quick-results';box.hidden=true;box.id='swQuickResults';form.appendChild(box);input.setAttribute('aria-controls',box.id);input.setAttribute('autocomplete','off');
 const rows=directoryRows();
 function draw(){const q=input.value.trim(),matches=quickMatches(rows,q);box.hidden=!q;if(!q){box.innerHTML='';return}box.innerHTML=matches.map(r=>'<a href="'+(r.registryOnly?'directory.html?q='+encodeURIComponent(r.figi):r.referenceOnly?'research.html?instrument='+encodeURIComponent(r.referenceId)+'#targetDetail':'company.html?ticker='+encodeURIComponent(r.ticker))+'"><strong>'+E(r.name)+'</strong><small>'+E(r.symbol||r.ticker)+' · '+E(r.exchange||'')+' · '+(r.referenceOnly?'Reference only':'Monitored')+'</small></a>').join('')+'<a class="sw-quick-all" href="stocks.html?q='+encodeURIComponent(q)+'">Search all research listings ↗</a><a class="sw-quick-all" href="stocks.html?universe=registry&amp;q='+encodeURIComponent(q)+'">Search full OpenFIGI catalog ↗</a>'}
 input.addEventListener('input',draw);input.addEventListener('focus',draw);form.addEventListener('keydown',e=>{if(e.key==='Escape'){box.hidden=true;input.focus()}if(e.key==='ArrowDown'&&e.target===input&&!box.hidden){e.preventDefault();box.querySelector('a')?.focus()}});document.addEventListener('click',e=>{if(!form.contains(e.target))box.hidden=true});
}
function stocks(){const registryMode=new URLSearchParams(location.search).get('universe')==='registry';let all=registryMode?referenceCatalogRows(state.referenceDirectory):directoryRows(),sect=[...new Set(all.map(c=>c.sector).filter(Boolean))].sort(),ex=[...new Set(all.map(c=>c.exchange).filter(Boolean))].sort(),params=new URLSearchParams(location.search);const licensed=licensedReferenceRows(state.licensedPrices,all);let chosen=sect.includes(params.get('sector'))?params.get('sector'):'All';let q=params.get('q')||'',sort='abs';let favoriteOnly=false;let currentPage=1;const pageSize=50;let favs;try{favs=new Set(JSON.parse(localStorage.getItem('stockwatch-v4-favorites')||'[]'))}catch{favs=new Set()};
$('v4app').innerHTML=`<div class="sw-grid4">${stat(registryMode?'OpenFIGI registry':'Research universe',N(all.length,0),registryMode?'Venue reference records':'Monitored + reference listings')}${stat('Observed closes',N(registryMode?0:priced().length,0),registryMode?'Registry does not contain prices':'Existing scanner only')}${stat('Reference without prices',N(all.filter(c=>c.referenceOnly&&!licensed.has(c.ticker)).length,0),'No licensed price series')}${stat('Exchanges',N(ex.length,0),'Trading venues')}</div><div class="sw-controls sw-universe-switch"><a class="sw-soft-btn ${registryMode?'':'active'}" href="stocks.html">Curated research universe · ${N(directoryRows().length,0)}</a><a class="sw-soft-btn ${registryMode?'active':''}" href="stocks.html?universe=registry">OpenFIGI reference catalog · ${state.referenceDirectory?N(state.referenceDirectory.records?.length||0,0):'Unavailable'}</a></div><p class="sw-meta">These are separate views, not additive counts. The expanded Nordic discovery selection uses collected OpenFIGI records, excluding known share-class and symbol overlaps; active or primary listing status still requires verification. Licensed end-of-day imports, when available, are labelled and kept separate from scanner calculations. <a class="sw-textlink" href="price-history.html">Historical coverage ↗</a></p><div class="sw-controls"><input type="search" id="stkSearch" placeholder="Search companies or tickers" value="${E(q)}"><select id="stkExchange"><option value="all">All exchanges</option>${ex.map(x=>`<option value="${E(x)}">${E(x)}</option>`).join('')}</select><select id="stkCoverage" aria-label="Price coverage"><option value="all">All research listings</option><option value="monitored">Monitored listings</option><option value="reference">Reference only</option></select><select id="stkSort"><option value="abs">Biggest moves</option><option value="gain">Top gainers</option><option value="loss">Top losers</option><option value="volume">Relative volume</option><option value="name">Company name</option><option value="volatility">Watchlist selection volatility</option></select><button id="favoriteOnly" class="sw-soft-btn" type="button" aria-pressed="false">☆ My watchlist</button></div><div class="sw-controls sw-screen-presets" ${registryMode?'hidden':''}><span class="sw-meta">Quick screens</span><button class="sw-soft-btn" data-screen="all" type="button">All listings</button><button class="sw-soft-btn" data-screen="moves" type="button">Moves ≥ 3%</button><button class="sw-soft-btn" data-screen="volume" type="button">Volume ≥ 2.5×</button><button class="sw-soft-btn" data-screen="signals" type="button">Unusual activity</button></div><details class="sw-panel sw-advanced-filters" ${registryMode?'hidden':''}><summary>Advanced price &amp; activity filters</summary><div class="sw-controls"><label>Min absolute 1D move (%)<input id="stkMove" type="number" min="0" step="0.1" placeholder="Any"></label><label>Min relative volume (×)<input id="stkVolume" type="number" min="0" step="0.1" placeholder="Any"></label><label>Min selection volatility (%)<input id="stkVolatility" type="number" min="0" step="1" placeholder="Any"></label><label class="sw-check-filter"><input id="stkSignal" type="checkbox"> Unusual activity only</label><button id="stkResetMetrics" class="sw-soft-btn" type="button">Clear metrics</button></div><p class="sw-meta">Missing values do not pass numeric filters. Thin listings are excluded from relative-volume filters. Selection volatility is the watchlist screening statistic, not a fresh rolling calculation. Relative-volume signals use the existing scanner thresholds.</p></details><p class="sw-meta sw-directory-note">Reference listings are searchable alongside monitored securities; they do not contribute to market breadth, price signals or returns. <a class="sw-textlink" href="research.html">Identity evidence &amp; historical coverage ↗</a></p><section class="sw-panel">${sectorChips(sect,chosen,'sector')}<div class="sw-panel-hd"><h2>Company directory</h2><small id="stockCount"></small></div><div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Company</th><th>Exchange</th><th>Last price</th><th>30D trend</th><th>1D change</th><th>Relative volume</th><th></th></tr></thead><tbody id="stocksRows"></tbody></table></div><div class="sw-ws-pagination"><button id="stockPrev" class="sw-soft-btn" type="button">← Previous</button><span id="stockPage" aria-live="polite"></span><button id="stockNext" class="sw-soft-btn" type="button">Next →</button></div></section><div id="stockDetail"></div>${onboardingPanel()}`;
function draw(){const query=$('stkSearch').value.trim().toLowerCase(),exchange=$('stkExchange').value,coverage=$('stkCoverage').value;const a=screenFinancialRows(all.filter(c=>(coverage==='all'||(coverage==='reference'?c.referenceOnly:!c.referenceOnly))&&(chosen==='All'||c.sector===chosen)&&(exchange==='all'||c.exchange===exchange)&&(!favoriteOnly||favs.has(c.ticker))&&(!query||`${c.name} ${c.symbol||c.ticker} ${c.sector} ${c.isin||''} ${c.figi||''} ${c.mic||''}`.toLowerCase().includes(query))),{move:$('stkMove').value,volume:$('stkVolume').value,volatility:$('stkVolatility').value,signal:$('stkSignal').checked});
const rank={abs:(x,y)=>Math.abs(y.changePct||0)-Math.abs(x.changePct||0),gain:(x,y)=>(y.changePct??-1e5)-(x.changePct??-1e5),loss:(x,y)=>(x.changePct??1e5)-(y.changePct??1e5),volume:(x,y)=>(y.rvol||0)-(x.rvol||0),name:(x,y)=>x.name.localeCompare(y.name),volatility:(x,y)=>(y.annualVolPct??-1)-(x.annualVolPct??-1)};a.sort((x,y)=>Number(!!x.unavailable)-Number(!!y.unavailable)||(rank[$('stkSort').value]||rank.abs)(x,y));$('stockCount').textContent=`${a.length} of ${all.length} research listings`;
const pages=Math.max(1,Math.ceil(a.length/pageSize));currentPage=Math.min(currentPage,pages);$('stockPrev').disabled=currentPage<=1;$('stockNext').disabled=currentPage>=pages;$('stockPage').textContent='Page '+currentPage+' of '+pages;$('stocksRows').innerHTML=a.slice((currentPage-1)*pageSize,currentPage*pageSize).map(c=>`<tr><td><button type="button" class="sw-favorite" data-fav="${E(c.ticker)}" aria-label="Toggle ${E(c.name)} on watchlist">${favs.has(c.ticker)?'★':'☆'}</button><strong>${E(c.name)}</strong><small>${E(c.symbol||c.ticker)} · ${E(c.sector||'Other')}</small></td><td>${E(c.exchange||'—')}</td><td>${licensed.has(c.ticker)?`<strong>${N(licensed.get(c.ticker).close,4)} ${E(licensed.get(c.ticker).currency)}</strong><small>Licensed EOD · ${E(licensed.get(c.ticker).lastDate)}</small>`:c.referenceOnly?'<span class="sw-pill warn">Reference only</span>':c.unavailable?'<span class="sw-pill warn">Unavailable</span>':`${N(c.close,3)} <small>${E(c.currency||'')}</small>`}</td><td>${chart(c.spark)}</td><td class="${sign(c.changePct)}">${c.unavailable?'—':P(c.changePct)}</td><td>${c.unavailable?'—':N(c.rvol)+'×'}</td><td>${licensed.has(c.ticker)?`<a class="sw-row-action" href="${licensedHistoryUrl(c.ticker)}">Price history ↗</a>`:c.registryOnly?`<a class="sw-row-action" href="directory.html?q=${encodeURIComponent(c.figi)}">Identity ↗</a>`:c.referenceOnly?`<a class="sw-row-action" href="research.html?instrument=${encodeURIComponent(c.referenceId)}#targetDetail">Research ↗</a>`:`<button type="button" class="sw-row-action" data-stock="${E(c.ticker)}">Details ↗</button>`}</td></tr>`).join('')||'<tr><td colspan="7" class="sw-empty">No companies match these filters.</td></tr>';}
const resetPage=()=>{currentPage=1;draw()};$('stockPrev').addEventListener('click',()=>{currentPage=Math.max(1,currentPage-1);draw()});$('stockNext').addEventListener('click',()=>{currentPage++;draw()});$('stkSearch').addEventListener('input',resetPage);$('stkExchange').addEventListener('change',resetPage);$('stkCoverage').addEventListener('change',resetPage);$('stkSort').addEventListener('change',resetPage);for(const id of ['stkMove','stkVolume','stkVolatility','stkSignal'])$(id).addEventListener('input',resetPage);const clearMetrics=()=>{for(const id of ['stkMove','stkVolume','stkVolatility'])$(id).value='';$('stkSignal').checked=false};$('stkResetMetrics').addEventListener('click',()=>{clearMetrics();resetPage()});document.querySelectorAll('[data-screen]').forEach(b=>b.addEventListener('click',()=>{clearMetrics();$('stkCoverage').value=b.dataset.screen==='all'?'all':'monitored';if(b.dataset.screen==='moves')$('stkMove').value='3';if(b.dataset.screen==='volume')$('stkVolume').value='2.5';if(b.dataset.screen==='signals')$('stkSignal').checked=true;document.querySelector('.sw-advanced-filters').open=b.dataset.screen!=='all';resetPage()}));document.querySelectorAll('[data-sector]').forEach(b=>b.addEventListener('click',()=>{currentPage=1;chosen=b.dataset.sector;document.querySelectorAll('[data-sector]').forEach(x=>x.classList.toggle('active',x===b));draw()}));$('favoriteOnly').addEventListener('click',()=>{currentPage=1;favoriteOnly=!favoriteOnly;$('favoriteOnly').classList.toggle('active',favoriteOnly);$('favoriteOnly').setAttribute('aria-pressed',String(favoriteOnly));draw()});$('stocksRows').addEventListener('click',e=>{const star=e.target.closest('[data-fav]');if(star){let t=star.dataset.fav;if(favs.has(t))favs.delete(t);else favs.add(t);try{localStorage.setItem('stockwatch-v4-favorites',JSON.stringify([...favs]))}catch{}draw();return}const b=e.target.closest('[data-stock]');if(b)openStock(b.dataset.stock)});if(registryMode)$('stkSort').value='name';draw();const requested=params.get('ticker')==='PERR.PA'?'ALPER.PA':params.get('ticker');if(requested)openStock(requested)}
async function getHistory(t){if(state.history.has(t))return state.history.get(t);if(state.missingHistory.has(t))return null;try{const d=await get('data/history/'+encodeURIComponent(t)+'.json');if(d.redistributionPermitted!==true||!d.licenseReference||!d.sourceUrl||!d.source||!d.currency||typeof d.adjusted!=='boolean'||!Array.isArray(d.bars)||!d.bars.length||d.ticker!==t)throw Error('unlicensed or empty');state.history.set(t,d);return d}catch{state.missingHistory.add(t);return null}}
/* V25: date-accurate charts and observation inspection. */
function chartSeries(bars){
 const map=new Map(),conflicts=new Set();
 for(const p of bars||[]){
  if(!p||typeof p.date!=='string'||!p.date||p.value==null||typeof p.value==='boolean'||!['number','string'].includes(typeof p.value)||String(p.value).trim()==='')continue;
  const t=Date.parse(p.date),v=Number(p.value);
  if(!Number.isFinite(t)||!Number.isFinite(v))continue;
  if(/^\d{4}-\d{2}-\d{2}$/.test(p.date)&&new Date(t).toISOString().slice(0,10)!==p.date)continue;
  if(map.has(t)&&map.get(t).value!==v)conflicts.add(t);
  else if(!map.has(t))map.set(t,{date:p.date,value:v,time:t});
 }
 return [...map.values()].filter(p=>!conflicts.has(p.time)).sort((a,b)=>a.time-b.time);
}
function chartWindow(bars,days){
 const s=chartSeries(bars),last=s.at(-1)?.time;
 return days?s.filter(p=>p.time>=last-days*86400000):s;
}
function chartCoordinates(s){
 const width=800,height=300,left=78,right=20,top=18,bottom=40;
 const lo=s.reduce((a,p)=>Math.min(a,p.value),Infinity),hi=s.reduce((a,p)=>Math.max(a,p.value),-Infinity);
 const pad=hi===lo?Math.max(Math.abs(hi)*.02,.01):(hi-lo)*.08,low=lo-pad,high=hi+pad;
 const t0=s[0].time,t1=s.at(-1).time;
 const points=s.map(p=>({...p,x:left+(p.time-t0)/(t1-t0||1)*(width-left-right),y:top+(high-p.value)/(high-low)*(height-top-bottom)}));
 return {width,height,left,right,top,bottom,low,high,points};
}
function lineGraph(bars,opts={}){
 const s=chartSeries(bars),label=opts.label||'Dated historical observations',unit=opts.unit||'';
 if(s.length<2)return '<div class="sw-chart-empty">'+E(opts.empty||'Dated historical prices are not available yet.')+'<small>'+(s.length?'One observation: '+E(s[0].date)+' · '+E(N(s[0].value,6))+' '+E(unit):'No validated observations in this selection.')+'</small></div>';
 const {width,height,left,right,top,bottom,low,high,points}=chartCoordinates(s),last=points.at(-1);
 const path=points.map((p,i)=>(i?'L':'M')+p.x.toFixed(2)+' '+p.y.toFixed(2)).join(' ');
 const grid=[0,1,2,3,4].map(i=>{const y=top+(height-top-bottom)*i/4;return '<line x1="'+left+'" x2="'+(width-right)+'" y1="'+y+'" y2="'+y+'" stroke="var(--sw-edge)"/><text x="'+(left-8)+'" y="'+(y+4)+'" text-anchor="end" class="sw-axis">'+E(N(high-(high-low)*i/4,4))+'</text>'}).join('');
 const ticks=[0,.5,1].map((v,i)=>'<text class="sw-axis" x="'+(left+(width-left-right)*v)+'" y="'+(height-12)+'" text-anchor="'+['start','middle','end'][i]+'">'+new Date(s[0].time+(last.time-s[0].time)*v).toISOString().slice(0,10)+'</text>').join('');
 return '<div class="sw-chart-pro" data-chart-points="'+E(JSON.stringify(points.map(p=>[p.date,p.value,p.x,p.y])))+'" data-chart-unit="'+E(unit)+'"><div class="sw-chart-pro-top"><div><strong>'+E(label)+'</strong><small>'+s.length+' observations · '+E(s[0].date)+' to '+E(last.date)+'</small></div><output class="sw-chart-readout">'+E(last.date)+' · '+E(N(last.value,6))+' '+E(unit)+'</output></div><div class="sw-graph large sw-chart-plot"><svg viewBox="0 0 800 300" preserveAspectRatio="none" role="img" aria-label="'+E(label)+'">'+grid+'<path d="'+path+'" stroke="'+E(opts.color||'var(--sw-mint)')+'" fill="none" stroke-width="2.3" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>'+ticks+'<line class="sw-chart-crosshair" x1="'+last.x+'" x2="'+last.x+'" y1="'+top+'" y2="'+(height-bottom)+'" stroke="var(--sw-muted)" stroke-dasharray="3 5"/><circle class="sw-chart-marker" cx="'+last.x+'" cy="'+last.y+'" r="4.5" fill="var(--sw-mint)" stroke="var(--sw-bg)"/></svg></div><div class="sw-chart-inspect"><label>Inspect recorded observation <input type="range" min="0" max="'+(s.length-1)+'" value="'+(s.length-1)+'" step="1" aria-label="'+E(label)+' observation"></label><small>Calendar spacing · lines connect recorded points only.</small></div></div>';
}
const chartPointCache=new WeakMap();
function chartPoints(host){if(!chartPointCache.has(host))chartPointCache.set(host,JSON.parse(host.dataset.chartPoints));return chartPointCache.get(host)}
function inspectChart(host,index){
 const pts=chartPoints(host),p=pts[Math.max(0,Math.min(pts.length-1,index))];if(!p)return;
 const marker=host.querySelector('.sw-chart-marker'),line=host.querySelector('.sw-chart-crosshair'),range=host.querySelector('input[type=range]'),out=host.querySelector('output');
 marker.setAttribute('cx',p[2]);marker.setAttribute('cy',p[3]);line.setAttribute('x1',p[2]);line.setAttribute('x2',p[2]);range.value=String(pts.indexOf(p));
 out.textContent=p[0]+' · '+N(p[1],6)+(host.dataset.chartUnit?' '+host.dataset.chartUnit:'');range.setAttribute('aria-valuetext',out.textContent);
}
function wireChartInspector(){
 document.addEventListener('input',e=>{const host=e.target.closest?.('.sw-chart-pro');if(host&&e.target.type==='range')inspectChart(host,Number(e.target.value))});
 document.addEventListener('pointermove',e=>{if(e.pointerType==='touch')return;const plot=e.target.closest?.('.sw-chart-plot');if(!plot)return;const host=plot.closest('.sw-chart-pro'),rect=plot.getBoundingClientRect();if(!rect.width)return;
 const x=(e.clientX-rect.left)*800/rect.width,pts=chartPoints(host);let lo=0,hi=pts.length-1;while(lo<hi){const mid=(lo+hi)>>1;if(pts[mid][2]<x)lo=mid+1;else hi=mid}
 if(lo>0&&Math.abs(pts[lo-1][2]-x)<Math.abs(pts[lo][2]-x))lo--;inspectChart(host,lo);
 });
}
function peerListings(all,c){return all.filter(x=>x.ticker!==c.ticker&&c.sector&&x.sector===c.sector).sort((a,b)=>Number(!!a.unavailable)-Number(!!b.unavailable)||String(a.name).localeCompare(String(b.name))).slice(0,8)}
function companyPage(){
 const ticker=new URLSearchParams(location.search).get('ticker');
 const root=$('v4app'),c=companies().find(x=>x.ticker===ticker);
 if(!c){root.innerHTML='<div class="sw-note">No tracked listing matches this identifier. <a class="sw-textlink" href="stocks.html">Explore tracked listings ↗</a></div>';return}
 document.title=c.name+' — Company research | Stockwatch';
 const heading=document.querySelector('.sw-page-head h1');if(heading)heading.textContent=c.name;
 root.innerHTML='<div id="stockDetail"></div>';return openStock(ticker);
}
async function openStock(t){
 const c=companies().find(x=>x.ticker===t);if(!c)return;
 const container=$('stockDetail');if(!container)return;
 const available=!c.unavailable&&Number.isFinite(c.close);
 const peers=peerListings(companies(),c);
 const researchUrl='company.html?ticker='+encodeURIComponent(c.ticker);
 const archive=storyData().filter(s=>s.ticker===c.ticker);
 const updates=(archive.length?archive:(c.stories||[])).slice().sort((a,b)=>Date.parse(b.published)-Date.parse(a.published)).slice(0,8);
 const detailId=encodeURIComponent(t);
 container.dataset.currentTicker=t;
 container.innerHTML='<section class="sw-panel sw-company-research"><div class="sw-company-banner"><div class="sw-company-emblem" aria-hidden="true">'+E(c.name.split(/\s+/).slice(0,2).map(s=>s[0]).join('').toUpperCase().slice(0,3))+'</div><div class="sw-company-heading"><div class="sw-ws-eyebrow">'+E(c.exchange||'Trading venue unknown')+' / '+E(c.ticker)+'</div><h2>'+E(c.name)+'</h2><p>'+E(c.sector||'Unclassified')+'</p></div><div class="sw-company-last"><small>Latest observed close</small><strong>'+E(available?N(c.close,3)+' '+(c.currency||''):'Unavailable')+'</strong><b class="'+sign(c.changePct)+'">'+E(available?P(c.changePct):'—')+'</b><small>'+E(state.signals?.generated?'Scan '+fmtDate(state.signals.generated):'No scan available')+'</small></div></div>'+
 '<div class="sw-company-links"><a class="sw-soft-btn" href="stocks.html">Stocks directory</a>'+(page==='company'?'':'<a class="sw-primary" href="'+researchUrl+'">Open full research page ↗</a>')+'<a class="sw-soft-btn" href="https://finance.yahoo.com/quote/'+encodeURIComponent(c.ticker)+'" target="_blank" rel="noopener noreferrer">External price source ↗</a></div>'+
 '<div class="sw-company-tabs" aria-label="Research sections">'+[['chart','Price & activity'],['financials','Financials'],['filings','Company updates'],['peers','Peers'],['identity','Identity']].map(([id,label])=>'<button type="button" data-company-tab="'+id+'" class="sw-soft-btn">'+label+'</button>').join('')+'</div>'+
 '<div class="sw-panel-pad"><div class="sw-company-block" data-company-section="chart"><div class="sw-stat-mini"><div><small>Relative volume</small><b>'+E(c.rvol==null?'—':N(c.rvol)+'×')+'</b></div><div><small>Vs watchlist market</small><b class="'+sign(c.excessPct)+'">'+P(c.excessPct)+'</b></div><div><small>Disclosed short</small><b>'+E(c.short?.percent==null?'—':N(c.short.percent)+'%')+'</b></div></div><div class="sw-section-row"><h2>Price history</h2><small>Source coverage determines available periods</small></div><div class="sw-controls">'+[[30,'1 month'],[90,'3 months'],[365,'1 year'],[1825,'5 years'],[0,'All available']].map(([d,l])=>'<button type="button" class="sw-soft-btn" data-period="'+d+'">'+l+'</button>').join('')+'</div><div class="sw-history-source" id="companyHistorySource">Checking history permissions…</div><div id="individualChart">Checking for dated history…</div><p class="sw-meta">Values are daily closes unless an adjusted series is verified. No simulated history or total-return calculation.</p></div>'+
 '<section class="sw-company-block" data-company-section="financials">'+renderFacts(c)+'</section>'+
 '<section class="sw-company-block" data-company-section="filings"><div class="sw-section-row"><h2>Company updates</h2><a class="sw-textlink" href="news.html?q='+encodeURIComponent(c.ticker)+'">All source-linked news ↗</a></div>'+(updates.map(s=>storyBrief({...s,name:c.name,ticker:c.ticker})).join('')||'<p class="sw-meta">No recent source-linked company updates available.</p>')+'</section>'+
 '<section class="sw-company-block" data-company-section="peers"><div class="sw-section-row"><h2>Sector peers</h2><a class="sw-textlink" href="stocks.html?sector='+encodeURIComponent(c.sector||'')+'">Explore sector ↗</a></div><p class="sw-meta">Peers share the Stockwatch sector classification; this is not a verified ownership, competitive or supply-chain relationship. Price changes use the latest scanner observations.</p><div class="sw-company-peers">'+(peers.map(p=>'<a class="sw-peer" href="company.html?ticker='+encodeURIComponent(p.ticker)+'"><strong>'+E(p.name)+'</strong><small>'+E(p.ticker)+' · '+E(p.exchange||'')+'</small><span class="'+sign(p.changePct)+'">'+E(p.unavailable?'Unavailable':P(p.changePct))+'</span></a>').join('')||'<div class="sw-note">No other tracked listing in this sector.</div>')+'</div></section>'+
 '<section class="sw-company-block" data-company-section="identity">'+instrumentIdentityPanel(c.ticker)+'</section>'+intelligencePanel(c)+'</div></section>';
 container.querySelectorAll('[data-company-tab]').forEach(b=>b.addEventListener('click',()=>{const section=container.querySelector('[data-company-section="'+b.dataset.companyTab+'"]');if(section)section.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'})}));
 if(page!=='company')container.scrollIntoView({behavior:'smooth',block:'start'});
 const hist=await getHistory(t);
 if(container.dataset.currentTicker!==t)return;
 const source=container.querySelector('#companyHistorySource');
 const allBars=hist?chartSeries(hist.bars.filter(x=>typeof x.close==='number'&&x.close>0).map(x=>({date:x.date,value:x.close}))):[];
 if(source)source.innerHTML=allBars.length?'<strong>Licensed historical close series</strong><span>'+E(hist.source)+' · '+E(hist.currency)+' · '+(hist.adjusted?'Adjusted closes (provider-defined)':'Unadjusted closes')+' · '+allBars.length+' observations</span><span>'+E(allBars[0].date)+' to '+E(allBars.at(-1).date)+'</span><a class="sw-textlink" href="'+E(link(hist.sourceUrl))+'" target="_blank" rel="noopener noreferrer">Source ↗</a> <a class="sw-textlink" href="'+E(link(hist.licenseReference))+'" target="_blank" rel="noopener noreferrer">Licence ↗</a>':'<strong>Licensed historical series not connected</strong><span>Latest scanner activity is separate from dated historical price data.</span><a class="sw-textlink" href="research.html">Historical coverage &amp; methodology ↗</a>';
 const paint=days=>{const target=container.querySelector('#individualChart');if(!target)return;container.querySelectorAll('[data-period]').forEach(b=>{b.classList.toggle('active',+b.dataset.period===days);b.setAttribute('aria-pressed',String(+b.dataset.period===days))});if(allBars.length){target.innerHTML=lineGraph(chartWindow(allBars,days),{label:c.name+' · daily close',unit:hist.currency});return}if(days===30&&c.spark?.length>1){target.innerHTML='<div class="sw-chart-empty"><strong>Undated recent scanner snapshot</strong><small>These closes lack individual date labels; this is not a dated price chart.</small><div class="sw-undated-spark">'+chart(c.spark,670,135)+'</div></div>';return}target.innerHTML=lineGraph([],{empty:'No licensed dated prices for this period.'})};
 container.querySelectorAll('[data-period]').forEach(b=>b.addEventListener('click',()=>paint(+b.dataset.period)));paint(30)
}
function onboardingPanel(){
 const rows=state.onboarding?.records||[];
 if(!rows.length)return '';
 return '<section class="sw-panel sw-onboarding">'+panelHeader('Research coverage expansion','Nordic directory','directory.html','Planned listings · no connected price feed')+'<div class="sw-panel-pad"><p class="sw-meta">'+rows.length+' additional Norwegian listings prioritized using exchange identity evidence. No change to the monitored universe until price access and identity mapping are established.</p><details><summary>View planned companies and ISINs</summary><div class="sw-onboard-grid">'+rows.map(x=>'<div><b>'+E(x.name)+'</b><small>'+E(x.ticker)+' · '+E(x.isin)+'</small></div>').join('')+'</div></details><p class="sw-meta"><a class="sw-textlink" href="'+E(link(state.onboarding.sourceUrl))+'" target="_blank" rel="noopener noreferrer">Original exchange reference ↗</a></p></div></section>';
}
function commodities(){const all=state.context?.commodities||[];let group='All';$('v4app').innerHTML=`<div class="sw-grid4">${stat('Metals',N(all.filter(x=>x.group==='metals').length,0),'Tracked market references')}${stat('Energy',N(all.filter(x=>x.group==='energy').length,0),'Tracked energy benchmarks')}${stat('Reported context',fmtDate(state.context?.generated),'Last saved data')}${stat('Source quality','Mixed','Direct quotes and labeled proxies')}</div><div class="sw-section-row"><h2>Market prices</h2><small>Latest known values · not live execution quotes</small></div><section class="sw-panel"><div class="sw-filter-row" id="commodityTabs"><button class="active" data-group="All">All markets</button><button data-group="metals">Metals</button><button data-group="energy">Energy</button></div><div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Commodity</th><th>Last</th><th>1 day</th><th>1 month</th><th>Year position</th><th>Source type</th></tr></thead><tbody id="commodityRows"></tbody></table></div></section>`;function draw(){let sub=group==='All'?all:all.filter(c=>c.group===group);$('commodityRows').innerHTML=sub.map(x=>`<tr><td><b>${E(x.name)}</b><small>${E(x.ticker||'')}</small></td><td>${N(x.last,3)}<small>${E(x.unit||'')}</small></td><td class="${sign(x.changePct)}">${P(x.changePct)}</td><td class="${sign(x.monthPct)}">${P(x.monthPct)}</td><td><div class="sw-valuebar"><i style="left:${Math.max(0,Math.min(97,Number(x.yearPosition||0)))}%"></i></div></td><td><span class="sw-pill ${x.proxy?'warn':''}">${x.proxy?'Proxy':'Market reference'}</span></td></tr>`).join('')};document.querySelectorAll('[data-group]').forEach(b=>b.addEventListener('click',()=>{group=b.dataset.group;document.querySelectorAll('[data-group]').forEach(x=>x.classList.toggle('active',x===b));draw()}));draw()}
function shorts(){const all=priced().filter(x=>x.short&&Number.isFinite(x.short.percent)).sort((a,b)=>b.short.percent-a.short.percent);$('v4app').innerHTML=`<div class="sw-grid4">${stat('Companies in register',N(all.length,0),'Tracked listings with records')}${stat('Highest disclosed',all.length?N(all[0].short.percent)+'%':'—',all[0]?.name||'No records')}${stat('Official register','Finanstilsynet','Norwegian disclosed holdings')}${stat('Not total interest','Thresholded','Small positions may be unreported')}</div><div class="sw-section-row"><h2>Disclosed short holdings</h2><a class="sw-textlink" target="_blank" rel="noopener noreferrer" href="https://ssr.finanstilsynet.no/">Official register ↗</a></div><section class="sw-panel"><div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Company</th><th>Current reported</th><th>Previous</th><th>Reporting funds</th><th>Largest holder</th><th>Register date</th></tr></thead><tbody>${all.map(x=>`<tr><td><b>${E(x.name)}</b><small>${E(x.ticker)}</small></td><td><b>${N(x.short.percent)}%</b></td><td>${N(x.short.previous)}%</td><td>${N(x.short.holders,0)}</td><td>${E(x.short.largest||'—')}<small>${x.short.largestPercent==null?'':N(x.short.largestPercent)+'%'}</small></td><td>${E(x.short.date||'')}</td></tr>`).join('')||'<tr><td colspan="6" class="sw-empty">No published short positions available.</td></tr>'}</tbody></table></div><div class="sw-note">Only publicly disclosed positions are listed. Older register entries may not represent current positions.</div></section>`}
function shipping(){const all=state.routes;let category='Dry bulk',query='';const selected=new Set();const previews=state.context?.freight||[];$('v4app').innerHTML=`<div class="sw-hero"><div><div class="sw-kicker">GLOBAL FREIGHT INTELLIGENCE</div><strong>Track ship classes and trade routes separately.</strong><p>Capesize, Newcastlemax, Panamax, Supramax, tankers and container trade lanes. Route descriptions are sourced; daily benchmarks need redistribution rights.</p></div><a class="sw-primary" href="https://www.balticexchange.com/en/data-services/market-information0/indices.html" target="_blank" rel="noopener noreferrer">Benchmark definitions ↗</a></div><div class="sw-grid4">${stat('Tracked route definitions',N(all.length,0),'Published benchmark catalog')}${stat('Capesize / Newcastlemax','Separate classes','Newcastlemax is not a quote')}${stat('Licensed prices','Not connected','No fabricated route rates')}${stat('Historical market data','Pending feed','Route history will follow provider access')}</div><div class="sw-section-row"><h2>Existing market proxies</h2><a class="sw-textlink" href="commodities.html">Related commodities ↗</a></div><div class="sw-tiles">${previews.map(x=>`<div class="sw-card sw-module" style="min-height:126px"><span class="sw-kicker">LISTED MARKET PROXY · NOT FREIGHT RATE</span><h3>${E(x.name)} · ${E(x.ticker||'')}</h3><p><strong>Security price ${N(x.last)} ${E(x.unit||'USD')}</strong> · <span class="${sign(x.changePct)}">${P(x.changePct)} today</span></p><small class="sw-meta">Not a direct shipping freight rate</small></div>`).join('')}</div><div class="sw-section-row"><h2>Routes & vessel classes</h2><small>Route units and source coverage</small></div><div class="sw-controls"><input id="routeSearch" placeholder="Search route, ship class, location…" type="search"><select id="routeVessel"><option value="all">All vessel classes</option></select></div><section class="sw-panel"><div id="shipCats" class="sw-filter-row"><button data-category="Dry bulk" class="active">Dry bulk</button><button data-category="Tankers">Tankers</button><button data-category="Containers">Containers</button></div><div class="sw-panel-pad"><div class="sw-route-list" id="routeGrid"></div></div></section><section id="routeCompare" class="sw-panel sw-compare-route" aria-live="polite"><div class="sw-panel-hd"><div><h2>Compare trade routes</h2><small>Select up to four definitions. Quotes are compared only with matching units and licensed rates.</small></div></div><div id="routeCompareBody" class="sw-panel-pad"><div class="sw-note">Select Compare from the route cards.</div></div></section><div id="routeDetail"></div><div class="sw-tips">A freight route assessed in USD/tonne must not be presented as USD/day earnings. Public display and redistribution of Baltic Exchange benchmarks generally requires a suitable licence. Historical rate curves will only be enabled for sourced, permitted datasets.</div>`;
let types=[...new Set(all.map(x=>x.vessel))].sort();$('routeVessel').innerHTML+=[...types].map(x=>`<option value="${E(x)}">${E(x)}</option>`).join('');function draw(){const vessel=$('routeVessel').value,words=$('routeSearch').value.toLowerCase();let arr=all.filter(x=>x.category===category&&(vessel==='all'||x.vessel===vessel)&&`${x.code} ${x.name} ${x.vessel}`.toLowerCase().includes(words));$('routeGrid').innerHTML=arr.map(x=>`<article class="sw-card sw-route"><div class="sw-route-id">${E(x.code)}</div><h3>${E(x.name)}</h3><p>${E(x.vessel)} · ${E(x.unit)}</p><div class="sw-route-foot">${x.quote!=null&&x.redistributionPermitted?`<b>${N(x.quote,3)} ${E(x.unit)}</b>`:'<span class="sw-pill warn">Price feed pending</span>'}<button class="sw-row-action" type="button" data-compare="${E(x.code)}" aria-pressed="${selected.has(x.code)}">${selected.has(x.code)?'✓ Selected':'Compare'}</button><button class="sw-row-action" type="button" data-route="${E(x.code)}">Details ↗</button></div></article>`).join('')||'<div class="sw-empty">No routes found for these filters.</div>'}document.querySelectorAll('[data-category]').forEach(b=>b.addEventListener('click',()=>{category=b.dataset.category;document.querySelectorAll('[data-category]').forEach(x=>x.classList.toggle('active',x===b));draw()}));$('routeGrid').addEventListener('click',e=>{const c=e.target.closest('[data-compare]');if(c){const id=c.dataset.compare;if(selected.has(id))selected.delete(id);else if(selected.size<4)selected.add(id);draw();paintCompare();return}const b=e.target.closest('[data-route]');if(b)showRoute(b.dataset.route)});
function paintCompare(){const arr=[...selected].map(code=>all.find(x=>x.code===code)).filter(Boolean);const target=$('routeCompareBody');if(!arr.length){target.innerHTML='<div class="sw-note">Choose two to four routes to compare vessel class, units, and data coverage.</div>';return}const units=[...new Set(arr.map(x=>x.unit))];target.innerHTML=`<div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Route</th><th>Vessel class</th><th>Units</th><th>Rate</th><th>History</th></tr></thead><tbody>${arr.map(x=>`<tr><td><strong>${E(x.code)}</strong><small>${E(x.name)}</small></td><td>${E(x.vessel)}</td><td>${E(x.unit)}</td><td>${x.redistributionPermitted&&Number.isFinite(x.quote)?N(x.quote,2):'Licensed quote unavailable'}</td><td>${x.redistributionPermitted?'Check source history':'Pending rights'}</td></tr>`).join('')}</tbody></table></div><div class="sw-note">${units.length>1?'These routes use different pricing units and must not be plotted on one numerical axis.':'Same quote units; date-aligned comparison is enabled only when verified price series exist.'} No rates are estimated from shipping ETFs.</div>`;}
$('routeSearch').addEventListener('input',draw);$('routeVessel').addEventListener('change',draw);draw();async function showRoute(code){const r=all.find(x=>x.code===code);if(!r)return;const node=$('routeDetail');node.innerHTML=`<div class="sw-panel sw-detail">${panelHeader(r.name,'Official definition',link(r.sourceUrl),`${r.code} · ${r.vessel} · ${r.unit}`)}<div class="sw-panel-pad"><div class="sw-kicker">HISTORICAL ROUTE DATA</div><div id="routeChart" class="sw-chart-empty">Checking licensed historical series…</div><p class="sw-meta">A historical route series is shown only when the source explicitly permits redistribution. Data is labeled by date and unit.</p></div></div>`;node.scrollIntoView({behavior:'smooth',block:'start'});try{let h=await get('data/freight-history/'+encodeURIComponent(code)+'.json');if(h.redistributionPermitted!==true||h.unit!==r.unit||h.code!==r.code||!h.licenseReference||!Array.isArray(h.observations))throw Error('unlicensed');let bars=h.observations.map(x=>({date:x.date,value:x.value}));$('routeChart').innerHTML=lineGraph(bars,{label:r.name+' freight history',unit:r.unit})}catch{$('routeChart').innerHTML=lineGraph([],{empty:'Licensed route history not connected yet.'})}}}

async function renderUSDAOceanIndices(){
 const host=$('v4app');if(!host)return;
 const panel=document.createElement('section');panel.className='sw-panel';panel.id='usdaShippingIndices';
 panel.innerHTML='<div class="sw-panel-hd"><div><h2>USDA ocean grain freight cost indices</h2><small>Actual weekly historical data · 2017 = 100 · not USD/tonne freight quotes</small></div></div><div class="sw-panel-pad"><div class="sw-note" id="usdaShippingContent">Checking USDA historical index data…</div></div>';
 const routePanel=$('routeCompare');if(routePanel)routePanel.parentNode.insertBefore(panel,routePanel);else host.appendChild(panel);
 const target=$('usdaShippingContent');
 let data;try{data=await get('data/shipping-open.json')}catch{target.textContent='USDA public data import has not run yet; route definitions and licensed-quote restrictions remain unchanged.';return}
 const series=(data?.series||[]).filter(x=>x&&x.isActualRate===false&&x.unit==='index, 2017 = 100'&&Array.isArray(x.history)&&x.history.length);
 if(!series.length){target.textContent='USDA historical observations are not available yet. Check Data Health for source status.';return}
 const status=data.source?.status;
 target.innerHTML='<p class="sw-meta">USDA Agricultural Marketing Service. Weekly transport-cost indices relative to 2017, not voyage quotes, ship earnings, or Baltic benchmarks. '
 + (status==='ok'?'Source refresh succeeded.':'Source refresh failed; showing earlier dated observations.')+'</p>'
 +'<div class="sw-grid4">'+series.map(x=>stat(E(x.route),N(x.value,2),'Index · 2017 = 100 · '+E(x.period||'unknown'))).join('')+'</div>'
 +'<div class="sw-controls"><label for="usdaIndexSelect">Compare historical index</label><select id="usdaIndexSelect">'+series.map((x,i)=>'<option value="'+i+'">'+E(x.route)+'</option>').join('')+'</select></div>'
 +'<div id="usdaIndexChart"></div><p class="sw-meta">Source: <a href="https://agtransport.usda.gov/Transportation-Costs/Grain-Transportation-Cost-Indicators/8uye-ieij" target="_blank" rel="noopener noreferrer">USDA AMS transportation indicators</a>. '
 +'Index bases: US Gulf to Japan $39.33/tonne and PNW to Japan $21.05/tonne in 2017, used only to construct each index. These are not current prices. '
 +'Newcastle, Capesize, Panamax and tanker route assessments still require licensed market data.</p>';
 const select=$('usdaIndexSelect'),chart=$('usdaIndexChart');
 const draw=()=>{const x=series[Number(select.value)||0];if(!x)return;
 const bars=x.history.filter(p=>p&&/^\d{4}-\d{2}-\d{2}$/.test(p.date)&&Number.isFinite(Number(p.value))).map(p=>({date:p.date,value:p.value}));
 chart.innerHTML=lineGraph(bars,{label:x.route+' · USDA index (2017=100)',unit:'index',empty:'At least two observations are required for a historical curve.'})
 };
 select.addEventListener('change',draw);draw();
}

async function renderWorldBankPortTraffic(){
 const host=$('v4app');if(!host)return;
 const panel=document.createElement('section');panel.className='sw-panel';panel.id='worldBankPortTraffic';
 panel.innerHTML='<div class="sw-panel-hd"><div><h2>Global container-port activity</h2><small>World Bank / UNCTAD · annual container throughput (TEU) · not freight prices</small></div></div><div class="sw-panel-pad"><div class="sw-note" id="worldBankPortContent">Checking annual container-port activity…</div></div>';
 const routePanel=$('routeCompare');if(routePanel)routePanel.parentNode.insertBefore(panel,routePanel);else host.appendChild(panel);
 const target=$('worldBankPortContent');
 let data;try{data=await get('data/shipping-ports.json')}catch{target.textContent='World Bank annual throughput importer has not published data yet.';return}
 const series=(data?.series||[]).filter(x=>x&&x.isActualRate===false&&x.unit==='TEU'&&x.frequency==='annual'&&Array.isArray(x.history)&&x.history.length);
 if(!series.length){target.textContent='No verified annual port-throughput observations yet. This is not a freight quotation. Check Data Health for the official-source status.';return}
 const status=data.source?.status;
 target.innerHTML='<p class="sw-meta">Country-level annual TEU totals include empty containers and transshipments. This is an activity indicator, not a live rate, vessel count, or port capacity. '
 +(status==='ok'?'World Bank source refresh succeeded.':'The last refresh is unavailable; dated historical observations are shown unchanged.')+'</p>'
 +'<div class="sw-grid4">'+series.slice(0,4).map(x=>stat(E(x.countryCode==='WLD'?'World':x.label),N(x.value,0),'TEU · '+E(x.period||'unknown year'))).join('')+'</div>'
 +'<div class="sw-controls"><label for="portCountrySelect">Select country / aggregate</label><select id="portCountrySelect">'+series.map((x,i)=>'<option value="'+i+'">'+E(x.label)+'</option>').join('')+'</select></div>'
 +'<div id="worldBankPortChart"></div><p class="sw-meta">Source: <a href="https://data.worldbank.org/indicator/IS.SHP.GOOD.TU" target="_blank" rel="noopener noreferrer">World Bank WDI / UNCTAD</a> · <a href="https://www.worldbank.org/ext/en/legal/terms-conditions/datasets" target="_blank" rel="noopener noreferrer">CC BY 4.0 and dataset terms</a>. These annual country totals are not comparable to daily Baltic, Braemar or Freightos shipping-rate quotations.</p>';
 const select=$('portCountrySelect'),chart=$('worldBankPortChart');
 const draw=()=>{const x=series[Number(select.value)||0];if(!x)return;
  const bars=x.history.filter(p=>p&&/^20\d{2}-12-31$/.test(p.date)&&Number.isFinite(Number(p.value))&&Number(p.value)>0).map(p=>({date:p.date,value:p.value}));
  chart.innerHTML=lineGraph(bars,{label:x.label+' · annual container port traffic (TEU)',unit:'TEU',empty:'At least two annual observations are required for a chart.'})
 };
 select.addEventListener('change',draw);draw();
}


async function renderUNCTADConnectivity(){
 const host=$('v4app');if(!host)return;
 const panel=document.createElement('section');panel.className='sw-panel';panel.id='unctadConnectivity';
 panel.innerHTML='<div class="sw-panel-hd"><div><h2>UNCTAD liner shipping connectivity</h2><small>Monthly container-network index · Q1 2023 average = 100 · NOT freight prices</small></div></div><div class="sw-panel-pad"><div class="sw-note" id="unctadContent">Checking UNCTAD data…</div></div>';
 const anchor=$('routeCompare');if(anchor)anchor.parentNode.insertBefore(panel,anchor);else host.appendChild(panel);
 const target=$('unctadContent');
 let data;try{data=await get('data/shipping-connectivity.json')}catch{target.textContent='Official monthly connectivity import has not published data yet.';return}
 const series=(data.series||[]).filter(x=>x&&x.isActualRate===false&&x.frequency==='monthly'&&x.unit==='index, Q1 2023 average = 100'&&Array.isArray(x.history)&&x.history.length);
 if(!series.length){target.textContent='No verified UNCTAD monthly connectivity observations yet. Data Health shows source status.';return}
 target.innerHTML='<p class="sw-meta">This UNCTAD index measures integration into liner container shipping networks. It does not measure freight rates, cargo throughput or port congestion. '+(data.source?.status==='ok'?'Source refresh succeeded.':'Displaying preserved dated observations; last refresh failed.')+'</p>'
 +'<div class="sw-grid4">'+series.slice(0,4).map(x=>stat(E(x.country),N(x.value,2),'LSCI · '+E(x.period||''))).join('')+'</div>'
 +'<div class="sw-controls"><label for="unctadCountry">Economy</label><select id="unctadCountry">'+series.map((x,i)=>'<option value="'+i+'">'+E(x.country)+'</option>').join('')+'</select></div><div id="unctadChart"></div>'
 +'<p class="sw-meta">Source: <a href="https://unctadstat.unctad.org/datacentre/dataviewer/US.LSCI_M" target="_blank" rel="noopener noreferrer">United Nations Trade and Development Data Hub (UNCTADstat)</a>. CC BY 3.0 IGO, attribution required. Original index values; dates shown are the months of observations.</p>';
 const select=$('unctadCountry'),chartNode=$('unctadChart');
 const draw=()=>{const x=series[Number(select.value)||0];if(!x)return;
  const bars=x.history.filter(p=>p&&/^20\d\d-(0[1-9]|1[0-2])-01$/.test(p.date)&&Number.isFinite(Number(p.value))&&p.value>0).map(p=>({date:p.date,value:p.value}));
  chartNode.innerHTML=lineGraph(bars,{label:x.country+' · UNCTAD monthly liner connectivity index',unit:'index',empty:'At least two dated UNCTAD observations required.'});
 };
 select.addEventListener('change',draw);draw();
}
function voyageCostScenario(v){
 const seaDays=(v.distance+v.ballast)/v.speed/24;
 const fuelTonnes=seaDays*v.burn+v.portDays*v.portBurn;
 const fuelUSD=fuelTonnes*v.fuel;
 const hireUSD=(seaDays+v.portDays)*v.hire;
 const subtotal=fuelUSD+hireUSD+v.portFees+v.other;
 const total=subtotal*(1+v.contingency/100);
 return {seaDays,fuelTonnes,fuelUSD,hireUSD,subtotal,total,perTonne:total/v.cargo};
}

function renderVoyageEstimator(){
 const host=$('v4app');if(!host)return;
 const usdRoutes=state.routes.filter(r=>r.category==='Dry bulk'&&r.unit==='USD/tonne');
 const panel=document.createElement('section');panel.className='sw-panel';panel.id='voyageEstimator';
 const fields=[
  ['distance','Loaded voyage distance (nautical miles)',11000,1,100000],
  ['ballast','Repositioning distance (nautical miles)',0,0,100000],
  ['speed','Average underway speed (knots)',12,1,30],
  ['burn','Fuel consumed underway (tonnes/day)',48,0,300],
  ['portDays','Port/idle time (days)',5,0,120],
  ['portBurn','Fuel consumed in port (tonnes/day)',5,0,100],
  ['fuel','Marine fuel price (USD/tonne)',600,0,10000],
  ['cargo','Loaded cargo (metric tonnes)',160000,1,500000],
  ['hire','Time charter / vessel cost (USD/day)',22000,0,300000],
  ['portFees','Port and canal costs (USD total)',100000,0,10000000],
  ['other','Other voyage costs (USD total)',0,0,10000000],
  ['contingency','Contingency (%)',10,0,100]
 ];
 panel.innerHTML='<div class="sw-panel-hd"><div><h2>Voyage cost scenario calculator</h2><small>Stockwatch independent model — hypothetical inputs, never a Baltic or Braemar quote</small></div></div>'
 +'<div class="sw-panel-pad"><p class="sw-meta">Explore a vessel voyage budget. All default values are hypothetical illustrations, not measured prices, physical route distances, or provider assessments. For any route, enter its actual distance and your own cost assumptions.</p>'
 +'<form id="voyageForm"><div class="sw-controls"><label for="voyageRoute">Scenario label</label><select id="voyageRoute">'+usdRoutes.map(r=>'<option value="'+E(r.code)+'">'+E(r.code+' · '+r.name)+'</option>').join('')+'</select></div>'
 +'<div class="sw-grid4">'+fields.map(([id,label,value,min,max])=>'<label class="sw-meta" style="display:grid;gap:6px">'+E(label)+'<input id="voyage_'+id+'" type="number" min="'+min+'" max="'+max+'" step="any" value="'+value+'" required class="sw-voyage-input"></label>').join('')+'</div>'
 +'<button class="sw-row-action" type="submit" style="margin:15px 0">Calculate scenario</button></form><div id="voyageResult" role="status" aria-live="polite"></div>'
 +'<p class="sw-meta">Model: sea days = (loaded distance + repositioning distance) / speed / 24; fuel cost = (sea days × underway consumption + port days × port consumption) × fuel price; vessel cost = (sea + port days) × daily hire. Total adds port, other and contingency costs. It excludes financing, commissions, demurrage, weather routing and cargo loss. Results are not tradable freight quotes.</p></div>';
 const anchor=$('routeCompare');if(anchor)anchor.parentNode.insertBefore(panel,anchor);else host.appendChild(panel);
 const form=$('voyageForm'),result=$('voyageResult');
 function calculate(){
  let vars={};for(const [id,,defaultValue,min,max] of fields){const n=Number($('voyage_'+id).value);if(!Number.isFinite(n)||n<min||n>max){result.textContent='Enter valid finite values within the displayed field limits.';return}vars[id]=n}
  const {seaDays,fuelTonnes,fuelUSD,hireUSD,subtotal,total,perTonne}=voyageCostScenario(vars);
  const money=x=>x.toLocaleString('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2});
  result.innerHTML='<div class="sw-grid4">'+
   stat('Modeled total cost',money(total),'USD · scenario estimate')+
   stat('Modeled cost per tonne',money(perTonne),'USD/tonne · NOT Baltic assessment')+
   stat('Estimated sea days',N(seaDays,2),'At user-entered speed')+
   stat('Estimated fuel cost',money(fuelUSD),N(fuelTonnes,2)+' tonnes of fuel')+
   '</div><p class="sw-meta">Cost breakdown: vessel '+money(hireUSD)+'; fuel '+money(fuelUSD)+'; port/canal '+money(vars.portFees)+'; other '+money(vars.other)+'; contingency '+money(total-subtotal)+'. Route selection is a label only; the calculator does not infer distances or market rates.</p>';
 }
 form.addEventListener('submit',e=>{e.preventDefault();calculate()});
 calculate();
}
function renderPortWatchPermission(){
 const host=$('v4app');if(!host)return;
 const panel=document.createElement('section');panel.className='sw-panel';panel.id='portWatchPermission';
 panel.innerHTML='<div class="sw-panel-hd"><div><h2>IMF PortWatch vessel activity</h2><small>Official port-call and chokepoint-transit signals · commercial reuse permission required</small></div></div>'
 +'<div class="sw-panel-pad"><p class="sw-meta">PortWatch provides publicly accessible maritime activity estimates, but its commercial redistribution and systematic-download permissions are not established for Stockwatch. No automated IMF feed is downloaded or displayed here until written permission is obtained. This is distinct from UNCTAD connectivity and Baltic freight assessments.</p>'
 +'<p><a class="sw-textlink" href="https://portwatch.imf.org/" target="_blank" rel="noopener noreferrer">View IMF PortWatch source ↗</a> · <a class="sw-textlink" href="https://www.imf.org/en/About/copyright-and-terms" target="_blank" rel="noopener noreferrer">IMF data usage terms ↗</a></p></div>';
 const anchor=$('routeCompare');if(anchor)anchor.parentNode.insertBefore(panel,anchor);else host.appendChild(panel);
}

function switchEstimate(p, direction, holding, feePct, slippagePct, flatFee){
 const from=direction==='A-to-B'?Number(p.aPrice):Number(p.bPrice);
 const to=direction==='A-to-B'?Number(p.bPrice):Number(p.aPrice);
 const amount=Number(holding),fee=Number(feePct)/100,slip=Number(slippagePct)/100,flat=Number(flatFee);
 if(![from,to,amount,fee,slip,flat].every(Number.isFinite)||from<=0||to<=0||amount<1||amount>100000000||fee<0||fee>.10||slip<0||slip>.10||flat<0||flat>1000000)return null;
 const sellPrice=from*(1-slip),sellGross=amount*sellPrice;
 const sellFee=Math.max(flat,sellGross*fee),proceeds=Math.max(0,sellGross-sellFee);
 const buyPrice=to*(1+slip);
 const byPct=Math.floor(proceeds/(buyPrice*(1+fee)));
 const byFlat=Math.floor((proceeds-flat)/buyPrice);
 const shares=Math.max(0,Math.min(byPct,byFlat));
 const buyGross=shares*buyPrice,buyFee=shares?Math.max(flat,buyGross*fee):0;
 const remainder=Math.max(0,proceeds-buyGross-buyFee);
 const drag=amount*from-sellGross+sellFee+shares*(buyPrice-to)+buyFee;
 const mean=Number(p.meanRatio),baseline=Number.isFinite(mean)&&mean>0?
    (direction==='A-to-B'?amount*mean:amount/mean):null;
 return {from,to,shares,remainder,drag,sellFee,buyFee,baseline,feeRate:fee,slipRate:slip};
}
function spreadCurrency(t){if(/\.OL$/.test(t))return 'NOK';if(/\.ST$/.test(t))return 'SEK';if(/\.CO$/.test(t))return 'DKK';return 'listing currency'}
function switchingCalculator(pair){return `<div class="sw-panel sw-switch"><div class="sw-panel-hd"><div><h2>Share-class switching calculator</h2><small>Illustrative transaction costs · no execution recommendation</small></div></div>
<div class="sw-panel-pad"><div class="sw-calc-grid"><label>Direction<select id="abDirection"><option value="A-to-B">Sell A · buy B</option><option value="B-to-A">Sell B · buy A</option></select></label><label>Shares held<input id="abHoldings" type="number" min="1" max="100000000" step="1" value="100"></label><label>Broker fee per leg (%)<input id="abFee" type="number" min="0" max="10" step="0.05" value="0.15"></label><label>Slippage per leg (%)<input id="abSlippage" type="number" min="0" max="10" step="0.05" value="0.20"></label><label>Minimum fee per leg<input id="abFlat" type="number" min="0" max="1000000" step="1" value="0"></label></div><div id="abCalcResult" role="status" aria-live="polite"></div><p class="sw-meta">Uses last scanner closing prices, not tradable bid/ask quotes. Taxes, FX conversion, settlement, liquidity and differences in voting rights are excluded. B shares may not have the same voting rights as A shares.</p></div></div>`}
function bindSwitchingCalculator(root,pair){const ids=['abDirection','abHoldings','abFee','abSlippage','abFlat'];
 const paint=()=>{const q=switchEstimate(pair,$('abDirection').value,$('abHoldings').value,$('abFee').value,$('abSlippage').value,$('abFlat').value),el=$('abCalcResult');
 if(!q){el.innerHTML='<div class="sw-note">Enter positive prices and valid, non-negative costs.</div>';return}
 const side=$('abDirection').value==='A-to-B'?'B':'A',cur=spreadCurrency(pair.a);
 el.innerHTML=`<div class="sw-spread-facts"><div><small>Estimated ${side} shares received</small><b>${N(q.shares,0)}</b></div><div><small>Unspent cash (${E(cur)})</small><b>${N(q.remainder,2)}</b></div><div><small>Execution costs + slippage (${E(cur)})</small><b>${N(q.drag,2)}</b></div><div><small>Shares at 1Y mean (before costs)</small><b>${q.baseline===null?'—':N(q.baseline,2)}</b></div></div><p class="sw-meta">Estimated fees: sell ${N(q.sellFee,2)} / buy ${N(q.buyFee,2)} ${E(cur)}. Reference comparison describes history, not an expected future conversion ratio.</p>`;
 };ids.forEach(id=>$(id)?.addEventListener('input',paint));paint();}
function spreadSnapshotChart(pair,days=0){const key=pair.a+'/'+pair.b,raw=state.observations?.pairs?.[key]||[],ok=raw.filter(x=>/^20\d\d-\d\d-\d\d$/.test(x.date)&&Number.isFinite(x.value)&&x.value>0).sort((a,b)=>a.date.localeCompare(b.date));
 const end=Date.parse(ok.at(-1)?.date),bars=days?ok.filter(x=>Date.parse(x.date)>=end-days*86400000):ok;
 if(bars.length<2)return '<div class="sw-chart-empty">Historical ratio snapshots are accumulating from scanner runs. Only '+bars.length+' dated observation(s) exist so far.<small>This is not a reconstructed 1Y price chart.</small></div>';
 // The public line starts from the first Stockwatch daily observation; it is
 // never retroactively synthesized from statistical summary data.
 return lineGraph(bars,{label:'Daily observed A/B ratio',unit:'A/B'})+`<p class="sw-meta">${bars.length} daily scanner observations · earliest ${E(bars[0].date)} · original indicator snapshots, not licensed share-price bars. One observation per UTC day.</p>`;
}
function ratioReference(a){
 const mean=Number(a.meanRatio),sd=Number(a.sd),now=Number(a.ratio);
 if(![mean,sd,now].every(Number.isFinite)||sd<=0)return '<div class="sw-note">No numeric one-year reference summary is available.</div>';
 // The reference band uses existing scanner statistics. It is not a dated price history.
 const low=mean-3*sd,high=mean+3*sd,position=Math.max(0,Math.min(100,(now-low)/(high-low)*100));
 const premium=Number.isFinite(a.aPrice)&&Number.isFinite(a.bPrice)&&a.bPrice>0?(a.aPrice/a.bPrice-1)*100:NaN;
 return `<div class="sw-ref-card"><div class="sw-section-row"><h2>Current ratio against 1Y reference</h2><small>Statistical summary — NOT a price-history chart</small></div><div class="sw-ref-track" role="img" aria-label="Current A/B ratio ${N(now,4)}, 1-year mean ${N(mean,4)}, plus or minus two standard deviations"><div class="sw-ref-band"></div><div class="sw-ref-mean"></div><div class="sw-ref-marker" style="left:${position.toFixed(2)}%"></div></div><div class="sw-ref-labels"><span>−2σ: ${N(mean-2*sd,4)}</span><span>Mean: ${N(mean,4)}</span><span>+2σ: ${N(mean+2*sd,4)}</span></div><div class="sw-spread-facts"><div><small>${E(a.a||'A class')} last</small><b>${N(a.aPrice,3)}</b></div><div><small>${E(a.b||'B class')} last</small><b>${N(a.bPrice,3)}</b></div><div><small>A premium vs B</small><b>${Number.isFinite(premium)?P(premium):'—'}</b></div><div><small>Observed sessions</small><b>${N(a.days,0)}</b></div></div><p class="sw-meta">The green line marks the 1Y mean and the bright marker the latest ratio. The shaded area is ±2 standard deviations, not a trading range or a reconstructed time series. Economic rights, liquidity and fees can explain a persistent premium.</p></div>`;
}
async function spreads(){const all=state.context?.shareClasses||[];if(!all.length){$('v4app').innerHTML='<div class="sw-note">Share-class data is unavailable in the latest market context.</div>';return}let chosen=all.find(x=>x.stationary&&x.tradableRange)||all[0];$('v4app').innerHTML=`<div class="sw-grid4">${stat('Tracked A/B pairs',N(all.length,0),'Derived from listed share classes')}${stat('Stationary candidates',N(all.filter(x=>x.stationary).length,0),'Based on existing stationarity checks')}${stat('Current context',fmtDate(state.context?.generated),'Latest observed pairs')}${stat('Ratio observations','Daily snapshots','Backfill only from licensed price series')}</div><div class="sw-section-row"><h2>Share class pairs</h2><small>Select a company for deeper analysis</small></div><div class="sw-pairs" id="spreadPairs"></div><section class="sw-panel" id="spreadDetail"></section><div class="sw-tips">Historical deviations are descriptive, not automatic buy/sell signals. Compare the same-day prices in the same currency, confirm identical economic rights, trading costs, liquidity, corporate actions and that a spread is statistically stable. A drifting pair should not be described as mean-reverting.</div>`;const host=$('spreadPairs');host.innerHTML=all.map((x,i)=>`<button data-pair="${i}" class="${x===chosen?'active':''}">${E(x.name)}</button>`).join('');host.addEventListener('click',e=>{let b=e.target.closest('[data-pair]');if(b){chosen=all[+b.dataset.pair];host.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));show()}});
async function show(){const a=chosen;const root=$('spreadDetail');root.innerHTML=`${panelHeader(`${a.name} · share-class ratio`,'Company comparisons','compare.html',`${a.a||'A class'} / ${a.b||'B class'}`)}<div class="sw-panel-pad"><div class="sw-spread-stats"><div><small>Current A/B ratio</small><b>${N(a.ratio,4)}</b></div><div><small>Difference vs 1Y mean</small><b>${a.stationary?N(a.z,2)+'σ':'Drifting'}</b></div><div><small>Observed range</small><b>${N(a.rangePct)}%</b></div><div><small>Time-series status</small><b>${a.stationary?'Stationary (tested)':'Not stationary'}</b></div></div>${ratioReference(a)}${switchingCalculator(a)}<div class="sw-panel sw-alerts"><div class="sw-panel-pad"><h2>In-page A/B threshold monitor</h2><div class="sw-controls"><label><input id="abFollow" type="checkbox"> Watch this pair</label><label>Z-score threshold <select id="abThreshold"><option value="1">1.0σ</option><option value="1.5">1.5σ</option><option value="2">2.0σ</option><option value="2.5">2.5σ</option></select></label></div><div id="abAlertText" class="sw-note" role="status"></div><small class="sw-meta">Only a browser-local watch condition, not email/push notifications. Alerts require a stationary candidate and cannot predict mean reversion.</small></div></div><div class="sw-section-row"><h2>Historical price ratio</h2><small>Same-day A ÷ B closes · licensed data only</small></div><div class="sw-chart-tools"><button type="button" data-spread-window="30">1M</button><button type="button" data-spread-window="90">3M</button><button type="button" data-spread-window="365" class="active">1Y</button><button type="button" data-spread-window="0">All</button></div><div id="spreadGraph" class="sw-chart-empty">Checking aligned, dated A/B prices…</div><div class="sw-metric-inline"><span>One-year reference ratio</span><b>${N(a.meanRatio,4)}</b></div><div class="sw-metric-inline"><span>Reported variation (standard deviation)</span><b>${N(a.sd,4)}</b></div><p class="sw-meta">Pair ${E(a.a||'A class')} vs ${E(a.b||'B class')}. The chart is only drawn when real source histories are available for both listings. It is not an execution signal.</p></div>`;
bindSwitchingCalculator(root,a);
const storeKey='stockwatch-final-pair-watches';let saved={};try{saved=JSON.parse(localStorage.getItem(storeKey)||'{}')||{}}catch{}
const watchId=a.a+'/'+a.b;
$('abFollow').checked=!!saved[watchId];$('abThreshold').value=String(saved[watchId]?.threshold||2);
const alertPaint=()=>{const limit=Number($('abThreshold').value),z=Number(a.z),trigger=a.stationary&&a.tradableRange&&Number.isFinite(z)&&Math.abs(z)>=limit;
 $('abAlertText').textContent=!a.stationary?'This pair failed the existing stability heuristic; no mean-reversion alert.':trigger?'Current ratio exceeds '+limit+'σ from the one-year mean. Review costs, liquidity and rights.':'Current ratio is below the selected threshold or insufficiently actionable.';
 $('abAlertText').classList.toggle('sw-alert-active',trigger&&$('abFollow').checked);
 try{if($('abFollow').checked)saved[watchId]={threshold:limit};else delete saved[watchId];localStorage.setItem(storeKey,JSON.stringify(saved))}catch{}
};$('abFollow').addEventListener('change',alertPaint);$('abThreshold').addEventListener('change',alertPaint);alertPaint();
const [ha,hb]=await Promise.all([getHistory(a.a),getHistory(a.b)]);if(chosen!==a)return;const graph=$('spreadGraph');if(!ha||!hb||ha.redistributionPermitted!==true||hb.redistributionPermitted!==true||!ha.currency||ha.currency!==hb.currency||ha.adjusted!==hb.adjusted){const paintObs=(days=365)=>{root.querySelectorAll('[data-spread-window]').forEach(b=>b.classList.toggle('active',Number(b.dataset.spreadWindow)===days));graph.innerHTML=spreadSnapshotChart(a,days)+`<p class="sw-meta">Licensed daily share-price histories are unavailable for this pair; showing only separately recorded Stockwatch ratio snapshots when available.</p>`};root.querySelectorAll('[data-spread-window]').forEach(b=>b.addEventListener('click',()=>paintObs(Number(b.dataset.spreadWindow))));paintObs();return}const aa=new Map((ha.bars||[]).filter(x=>x.date&&x.close>0).map(x=>[x.date,+x.close]));const bb=new Map((hb.bars||[]).filter(x=>x.date&&x.close>0).map(x=>[x.date,+x.close]));const points=[...aa.entries()].filter(([d,v])=>bb.has(d)&&bb.get(d)>0).map(([d,v])=>({date:d,value:v/bb.get(d)})).sort((x,y)=>x.date.localeCompare(y.date));const paint=(windowDays=365)=>{root.querySelectorAll('[data-spread-window]').forEach(b=>b.classList.toggle('active',Number(b.dataset.spreadWindow)===windowDays));const latest=Date.parse(points.at(-1)?.date);const display=windowDays?points.filter(p=>Date.parse(p.date)>=latest-windowDays*86400000):points;graph.innerHTML=lineGraph(display,{label:'Historical A to B price ratio',unit:'A/B',empty:'Not enough licensed price observations in this date range.'})+`<p class="sw-meta">${N(display.length,0)} aligned observations · ${E(ha.source||'Price source')} / ${E(hb.source||'Price source')} · ${E(ha.currency)}. Split/dividend adjustments and share-class rights must be verified.</p>`};root.querySelectorAll('[data-spread-window]').forEach(b=>b.addEventListener('click',()=>paint(Number(b.dataset.spreadWindow))));paint()}
await show()}
async function renderOpenMacro(){
 const app=$('v4app');
 if(!app)return;
 const host=document.createElement('section');
 host.className='sw-panel';
 host.id='officialMacro';
 host.innerHTML='<div class="sw-panel-pad"><div class="sw-section-row"><h2>Official macro & FX datasets</h2><a class="sw-textlink" href="health.html">Data sources & reliability ↗</a></div><p class="sw-meta">Official statistics and reference rates, not executable trading quotes. Original source attribution is shown with each series.</p><div id="macroSeriesContent" class="sw-note">Loading official data…</div></div>';
 app.appendChild(host);
 const area=$('macroSeriesContent');
 const results=await Promise.allSettled([get('data/open-data.json'),get('data/economic-feeds.json')]);
 const merged=results.flatMap(r=>r.status==='fulfilled'?(r.value.series||[]):[]);
 const series=merged.filter(x=>x&&Array.isArray(x.history)&&x.history.length&&Number.isFinite(Number(x.value)));
 if(!series.length){area.textContent='No validated official observations have been collected yet. Source health will show which feeds are pending.';return}
 const preferred=series.filter(x=>x.key.startsWith('fx:')||x.key.startsWith('hicp_yoy:')||x.key.includes('NY.GDP.MKTP.KD.ZG'));
 const economics=series.filter(x=>x.key.startsWith('fred:')||x.key.startsWith('eia:'));
 const chosen=[...economics,...preferred,...series].filter((x,i,a)=>a.findIndex(y=>y.key===x.key)===i).slice(0,60);
 area.innerHTML='<div class="sw-filter-row"><label for="officialSeriesSelect">Official time series</label><select id="officialSeriesSelect" aria-label="Choose an official statistical series">'+chosen.map((x,i)=>'<option value="'+i+'">'+E(x.label)+' · '+E(x.country)+'</option>').join('')+'</select></div><div id="officialSeriesDetails"></div>';
 const select=$('officialSeriesSelect'),detail=$('officialSeriesDetails');
 const paint=()=>{
  const x=chosen[Number(select.value)||0],source=link(x.sourceUrl);
  if(!x)return;
  const points=x.history.filter(v=>v&&Number.isFinite(Number(v.value))&&/^\d{4}-\d{2}-\d{2}$/.test(v.date));
  detail.innerHTML='<div class="sw-grid4">'+stat('Latest official observation',N(x.value,4),E(x.unit||''))+
    stat('Observation period',E(x.period||'Unknown'),'Historical reference date')+
    stat('Publisher',E(x.provider||'Official source'),'Attributed source')+
    stat('Data collected',fmtDate(x.observedAt),'Not necessarily latest market date')+'</div>'+
    lineGraph(points,{label:x.label+' — official observations',unit:x.unit||'',empty:'Only one dated observation is currently available.'})+
    '<p class="sw-meta">Source: '+(source?'<a href="'+E(source)+'" target="_blank" rel="noopener noreferrer">'+E(x.provider)+'</a>':E(x.provider))+
    ' · License/reuse: '+E(x.license||'Check source terms')+' · Frequency: '+E(x.frequency||'Unknown')+
    ' · For reference only; not an executable stock price or freight quote.</p>';
 };
 select.addEventListener('change',paint);paint();
}
function nav(){const group=document.querySelector('.sw-nav-group:last-child .sw-links');if(group){for(const [href,label,icon] of [['welcome.html','About Stockwatch','◫'],['directory.html','Instrument directory','▥'],['research.html','Research methodology','◉'],['intelligence.html','Intelligence graph','◇']]){if(group.querySelector('a[href="'+href+'"]'))continue;const a=document.createElement('a');a.className='sw-link';a.href=href;const i=document.createElement('span');i.className='sw-link-icon';i.textContent=icon;const t=document.createElement('span');t.textContent=label;a.append(i,t);group.appendChild(a)}}const mark=document.querySelector('.sw-logo-mark');if(mark){const img=document.createElement('img');img.src='brand/stockwatch.svg';img.alt='';img.width=36;img.height=36;mark.replaceChildren(img)}const favicon=document.querySelector('link[rel="icon"]');if(favicon)favicon.href='brand/stockwatch.svg';let theme;try{theme=localStorage.getItem('stockwatch-theme')}catch{}theme=theme==='light'?'light':'dark';document.body.dataset.theme=theme;$('swTheme').textContent=theme==='light'?'☀':'☾';$('swTheme').onclick=()=>{let now=document.body.dataset.theme==='light'?'dark':'light';document.body.dataset.theme=now;$('swTheme').textContent=now==='light'?'☀':'☾';try{localStorage.setItem('stockwatch-theme',now)}catch{}};$('swSearchForm').addEventListener('submit',e=>{e.preventDefault();let q=$('swGlobalSearch').value.trim();location.href='stocks.html'+(q?'?q='+encodeURIComponent(q):'')});document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('swGlobalSearch').focus()}})}
async function init(){nav();wireChartInspector();const files=[['signals','data/signals.json'],['context','data/context.json'],['watchlist','watchlist.json'],['routes','data/freight-routes.json'],['archive','data/news-latest.json'],['health','data/source-health.json'],['fundamentals','data/fundamentals.json'],['observations','data/spread-observations.json'],['identities','data/registered-source-status.json'],['issuers','data/issuer-identities.json'],['onboarding','data/research-onboarding.json'],['researchTargets','data/research-targets.json'],['researchCoverage','data/research-coverage.json'],['intelligence','data/intelligence-context.json'],['expansion','data/research-expansion.json'],['licensedPrices','data/licensed-price-coverage.json'],...(['index','stocks'].includes(page)?[['referenceDirectory','data/instrument-directory.json']]:[])];const data=await Promise.all(files.map(async([k,p])=>{try{return [k,await get(p)]}catch{return [k,null]}}));const o=Object.fromEntries(data);state.signals=o.signals;state.context=o.context;state.watchlist=o.watchlist?.tickers||[];state.routes=o.routes?.routes||[];state.archive=o.archive;state.health=o.health;state.fundamentals=o.fundamentals?.companies||{};state.observations=o.observations;state.identities=o.identities;state.issuers=o.issuers;state.onboarding=o.onboarding;state.researchTargets=o.researchTargets;state.researchCoverage=o.researchCoverage;state.intelligence=o.intelligence;state.referenceDirectory=o.referenceDirectory;state.expansion=o.expansion;state.licensedPrices=o.licensedPrices;wireQuickSearch();const label=$('swRefreshLabel');if(state.signals?.generated)label.textContent='Updated '+timeAge(state.signals.generated);else label.textContent='Data unavailable';if(state.signals?.generated)$('swSourceStatus').textContent='Last scan '+fmtDate(state.signals.generated);tape();if(['news','calendar','compare','health'].includes(page))return;if((!state.watchlist.length&&!(['stocks','intelligence'].includes(page)&&state.researchTargets?.targets?.length))||(!state.signals&&!['index','stocks','company','intelligence','licensedPrices'].includes(page))){$('v4app').innerHTML='<div class="sw-note sw-notice">The scanner dataset is unavailable. The interface does not invent market data.</div>';return}if(page==='index')overview();else if(page==='stocks')stocks();else if(page==='licensedPrices')await licensedPricePage();else if(page==='company')await companyPage();else if(page==='intelligence')await intelligencePage();else if(page==='spreads')await spreads();else if(page==='shipping'){shipping();await renderUSDAOceanIndices();await renderWorldBankPortTraffic();await renderUNCTADConnectivity();renderVoyageEstimator();renderPortWatchPermission();}else if(page==='commodities'){commodities();await renderOpenMacro();}else if(page==='shorts')shorts()}
init().catch(e=>{if($('v4app'))$('v4app').innerHTML=`<div class="sw-note sw-notice">Could not render this page: ${E(e.message)}</div>`;console.error(e)});
})();
