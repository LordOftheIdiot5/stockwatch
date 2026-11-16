/* Stockwatch native research terminal — display existing source-linked observations. */
(function(){
'use strict';
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const number=v=>typeof v==='number'&&Number.isFinite(v);
const fmt=(v,d=2)=>number(v)?v.toLocaleString('en-GB',{maximumFractionDigits:d}):'—';
const pct=v=>number(v)?(v>0?'+':'')+v.toFixed(2)+'%':'—';
const tone=v=>number(v)?v>0?'sw-up':v<0?'sw-down':'sw-neutral':'sw-neutral';
const dateOk=d=>typeof d==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d))&&new Date(d).toISOString().slice(0,10)===d;
const safeUrl=u=>{try{const a=new URL(u);return a.protocol==='https:'?a.href:''}catch{return ''}};
const get=async p=>{const r=await fetch(p,{cache:'no-store'});if(!r.ok)throw Error('Unavailable');return r.json()};
const colors=['#179e81','#618cf5','#e59a46','#bc83e7','#df7089'];
function points(rows){
 const m=new Map(),bad=new Set();
 for(const r of rows||[]){if(!dateOk(r.date)||!number(r.value))continue;if(m.has(r.date)&&m.get(r.date)!==r.value)bad.add(r.date);else m.set(r.date,r.value)}
 return [...m].filter(([d])=>!bad.has(d)).sort(([a],[b])=>a.localeCompare(b)).map(([date,value])=>({date,value}));
}
function compareSeries(series,days){
 const clean=series.map(s=>({...s,points:points(s.history)})).filter(s=>s.points.length);
 if(!clean.length)return [];
 const end=Math.min(...clean.map(s=>Date.parse(s.points.at(-1).date))),start=days?end-days*86400000:-Infinity;
 const sets=clean.map(s=>new Map(s.points.filter(p=>Date.parse(p.date)>=start&&Date.parse(p.date)<=end).map(p=>[p.date,p.value])));
 const dates=[...sets[0].keys()].filter(d=>sets.every(m=>m.has(d)));
 if(!dates.length||sets.some(m=>m.get(dates[0])<=0))return [];
 return clean.map((s,i)=>({...s,points:dates.map(date=>({date,value:sets[i].get(date)/sets[i].get(dates[0])*100,raw:sets[i].get(date)}))}));
}
function newsRelevant(s){
 const headline=(s.english||s.headline||'').toLowerCase();
 if(s.regulatory||s.kind==='disclosure')return true;
 if(/\b(formula 1|team order|sap arena|traffic accident|traffic standstill|grand prix|race review)\b/.test(headline))return /\b(earnings|revenue|profit|guidance|acquisition|dividend|financial results)\b/.test(headline);
 return number(s.material)&&s.material>=2;
}
function loadPrefs(){try{return JSON.parse(localStorage.getItem('stockwatch-terminal-v31')||'{}')||{}}catch{return {}}}
function persist(x){try{localStorage.setItem('stockwatch-terminal-v31',JSON.stringify(x))}catch{}}
function panel(title,sub,body,id=''){return '<section class="sw-terminal-panel" '+(id?'id="'+id+'"':'')+'><header><strong>'+esc(title)+'</strong><small>'+esc(sub)+'</small></header><div class="sw-terminal-body">'+body+'</div></section>'}
function table(head,body){return '<div class="sw-terminal-scroll"><table><thead><tr>'+head.map(x=>'<th>'+esc(x)+'</th>').join('')+'</tr></thead><tbody>'+body+'</tbody></table></div>'}
function chart(host,series,onWindow){
 const out=series.filter(s=>s.points.length);
 host.replaceChildren();
 if(!out.length||out[0].points.length<2){host.textContent='Insufficient dated observations for this range. No values are generated.';return}
 const W=800,H=300,L=64,R=20,T=16,B=34;
 const min=Math.min(...out.flatMap(s=>s.points.map(p=>p.value))),max=Math.max(...out.flatMap(s=>s.points.map(p=>p.value)));
 const pad=Math.max((max-min)*.08,Math.abs(max)*.005,.01),lo=min-pad,hi=max+pad;
 const dates=out[0].points.map(p=>p.date),t0=Date.parse(dates[0]),t1=Date.parse(dates.at(-1));
 const X=p=>L+(Date.parse(p.date)-t0)/(t1-t0||1)*(W-L-R),Y=v=>T+(hi-v)/(hi-lo)*(H-T-B);
 const svg='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="Dated research comparison chart" class="sw-terminal-svg">'+Array.from({length:5},(_,i)=>{const y=T+i*(H-T-B)/4;return '<line x1="'+L+'" y1="'+y+'" x2="'+(W-R)+'" y2="'+y+'" class="sw-terminal-gridline"/><text x="'+(L-7)+'" y="'+(y+4)+'" text-anchor="end">'+fmt(hi-i*(hi-lo)/4,2)+'</text>'}).join('')+out.map((s,i)=>'<polyline fill="none" stroke="'+colors[i]+'" stroke-width="2.1" vector-effect="non-scaling-stroke" points="'+s.points.map(p=>X(p).toFixed(2)+','+Y(p.value).toFixed(2)).join(' ')+'"/>').join('')+'<line data-crosshair x1="'+L+'" x2="'+L+'" y1="'+T+'" y2="'+(H-B)+'" class="sw-terminal-crosshair" visibility="hidden"/><text x="'+L+'" y="'+(H-9)+'">'+dates[0]+'</text><text x="'+(W-R)+'" y="'+(H-9)+'" text-anchor="end">'+dates.at(-1)+'</text></svg>';
 host.innerHTML=svg+'<div class="sw-terminal-inspector" aria-live="polite"></div><label class="sw-terminal-range">Inspect date <input aria-label="Inspect observation date" type="range" min="0" max="'+(dates.length-1)+'" value="'+(dates.length-1)+'"></label>';
 const range=host.querySelector('input'),line=host.querySelector('[data-crosshair]'),info=host.querySelector('.sw-terminal-inspector'),plot=host.querySelector('svg');
 function inspect(i){const ix=Math.max(0,Math.min(dates.length-1,i));range.value=String(ix);const d=dates[ix],x=X({date:d});line.setAttribute('x1',x);line.setAttribute('x2',x);line.setAttribute('visibility','visible');info.innerHTML='<strong>'+esc(d)+'</strong>'+out.map((s,j)=>{const p=s.points.find(p=>p.date===d);return '<span><i style="background:'+colors[j]+'"></i>'+esc(s.label)+': '+(p?fmt(p.raw??p.value)+' '+esc(s.unit)+(p.raw!==undefined?' · '+fmt(p.value)+' index':''):'—')+'</span>'}).join('')}
 range.oninput=()=>inspect(+range.value);
 plot.addEventListener('pointermove',e=>{const r=plot.getBoundingClientRect();const px=(e.clientX-r.left)/r.width*W;let i=0,best=Infinity;dates.forEach((d,j)=>{const delta=Math.abs(X({date:d})-px);if(delta<best){i=j;best=delta}});inspect(i)});
 plot.addEventListener('dblclick',()=>onWindow?.());
 inspect(dates.length-1);
}
async function render({root,companies,universe,signals,context,licensedPrices}){
 const pref=loadPrefs(),known=new Map(universe.map(r=>[r.ticker,r]));
 let selected=known.has(pref.selected)?pref.selected:companies.find(r=>!r.unavailable)?.ticker||universe[0]?.ticker||'';
 let sector=typeof pref.sector==='string'?pref.sector:'all',query='',pinned=new Set(Array.isArray(pref.pinned)?pref.pinned.filter(x=>known.has(x)):[]),watchOnly=false,days=[30,90,365,0].includes(pref.days)?pref.days:365,mode=pref.mode==='raw'?'raw':'normalized';
 const results=await Promise.allSettled([get('data/open-data.json'),get('data/economic-feeds.json')]);
 const series=results.flatMap(r=>r.status==='fulfilled'?r.value.series||[]:[]).filter(s=>s.key&&safeUrl(s.sourceUrl)&&points(s.history).length>=2);
 const byKey=new Map(series.map(s=>[s.key,s]));
 let keys=(Array.isArray(pref.keys)?pref.keys:['eia:RBRTE','eia:RWTC','fx:USD/NOK']).filter(k=>byKey.has(k)).slice(0,5);
 if(!keys.length&&series.length)keys=[series[0].key];
 let gen=0;
 const save=()=>persist({selected,sector,pinned:[...pinned],keys,days,mode});
 root.innerHTML='<div class="sw-terminal-head"><div><small class="sw-ws-eyebrow">STOCKWATCH / RESEARCH WORKSPACE</small><h1>Market terminal</h1><p>Linked equity research · official macro series · source-aware charts</p></div><div class="sw-terminal-status"><span>'+esc(signals?.generated?'Scan '+signals.generated.slice(0,16).replace('T',' ')+' UTC':'Scanner unavailable')+'</span><button type="button" class="sw-soft-btn" id="terminalReset">Reset workspace</button></div></div><div class="sw-terminal-layout"><div class="sw-terminal-left">'+panel('Equity universe',universe.length+' listings','<div class="sw-terminal-filter"><input id="terminalQuery" type="search" placeholder="Ticker or company" aria-label="Filter equity universe"><select id="terminalSector" aria-label="Sector filter"><option value="all">All sectors</option>'+[...new Set(universe.map(r=>r.sector).filter(Boolean))].sort().map(s=>'<option>'+esc(s)+'</option>').join('')+'</select><label><input id="terminalWatch" type="checkbox"> Watchlist only</label></div><div id="terminalEquities"></div>','terminalEquityPanel')+panel('Sector breadth','Scanner observations','<div id="terminalSectors"></div>')+'</div><div class="sw-terminal-center">'+panel('Selected instrument','Linked workspace','<div id="terminalInstrument"></div>')+panel('Historical comparison','Native Stockwatch chart','<div class="sw-terminal-controls"><select id="terminalMode" aria-label="Chart scale"><option value="normalized">Normalized · base 100</option><option value="raw">Single series · original units</option></select><div id="terminalPeriods">'+[[30,'1M'],[90,'3M'],[365,'1Y'],[0,'All']].map(([n,l])=>'<button type="button" class="sw-soft-btn" data-terminal-days="'+n+'">'+l+'</button>').join('')+'</div></div><div id="terminalChart" class="sw-terminal-chart"></div><div id="terminalChartSources"></div>')+panel('Company intelligence','Financially relevant headlines','<div id="terminalNews"></div>')+'</div><div class="sw-terminal-right">'+panel('Series selector','Choose up to five','<div id="terminalSeries"></div>')+panel('Commodities & freight','Latest scanner observations','<div id="terminalCommodities"></div>')+panel('A/B share research','Observed share-class ratios','<div id="terminalPairs"></div>')+'</div></div>';
 const $=id=>root.querySelector('#'+id);
 $('terminalSector').value=[...$('terminalSector').options].some(o=>o.value===sector)?sector:'all';sector=$('terminalSector').value;
 $('terminalMode').value=mode;
 function drawEquities(){
  const rows=universe.filter(r=>(sector==='all'||r.sector===sector)&&(!watchOnly||pinned.has(r.ticker))&&(!query||[r.name,r.ticker,r.symbol,r.figi].join(' ').toLowerCase().includes(query)));
  const ordered=rows.sort((a,b)=>Number(pinned.has(b.ticker))-Number(pinned.has(a.ticker))||((number(b.changePct)?Math.abs(b.changePct):-1)-(number(a.changePct)?Math.abs(a.changePct):-1))||String(a.name).localeCompare(b.name));
  $('terminalEquities').innerHTML=table(['Company','Last','1D'],ordered.slice(0,150).map(r=>'<tr class="'+(r.ticker===selected?'selected':'')+'"><td><button type="button" class="sw-terminal-row" data-terminal-ticker="'+esc(r.ticker)+'"><b>'+esc(r.name)+'</b><small>'+esc(r.symbol||r.ticker)+'</small></button></td><td>'+(!r.referenceOnly&&!r.unavailable&&number(r.close)?fmt(r.close)+' <small>'+esc(r.currency)+'</small>':'—')+'</td><td class="'+tone(r.changePct)+'">'+(!r.referenceOnly&&!r.unavailable?pct(r.changePct):'—')+'</td></tr>').join('')||'<tr><td colspan="3">No matches</td></tr>')+'<small class="sw-terminal-foot">'+Math.min(rows.length,150)+' of '+rows.length+' matching listings · search to narrow</small>';
 }
 function drawSectors(){
  const groups=new Map();for(const c of companies){if(c.unavailable||!number(c.changePct))continue;const k=c.sector||'Other';if(!groups.has(k))groups.set(k,[]);groups.get(k).push(c.changePct)}
  $('terminalSectors').innerHTML=table(['Sector','Up / down','Mean 1D'],[...groups].sort((a,b)=>a[0].localeCompare(b[0])).map(([k,v])=>{const m=v.reduce((a,b)=>a+b,0)/v.length;return '<tr><td><button class="sw-terminal-row" type="button" data-terminal-sector="'+esc(k)+'">'+esc(k)+'</button></td><td>'+v.filter(x=>x>0).length+' / '+v.filter(x=>x<0).length+'</td><td class="'+tone(m)+'">'+pct(m)+'</td></tr>'}).join(''));
 }
 function drawInstrument(){
  const r=known.get(selected);if(!r){$('terminalInstrument').textContent='Choose a listing.';return}
  const valid=!r.referenceOnly&&!r.unavailable&&number(r.close),href=r.referenceOnly?'price-history.html?listing='+encodeURIComponent(r.ticker):'company.html?ticker='+encodeURIComponent(r.ticker);
  $('terminalInstrument').innerHTML='<div class="sw-terminal-instrument"><div><h2>'+esc(r.name)+'</h2><small>'+esc(r.symbol||r.ticker)+' · '+esc(r.exchange||r.mic||'')+'</small></div><div class="sw-terminal-quote"><strong>'+ (valid?fmt(r.close)+' '+esc(r.currency):'No observed price')+'</strong><small class="'+tone(r.changePct)+'">'+(valid?pct(r.changePct):'Reference only')+'</small></div></div><div class="sw-terminal-controls"><button class="sw-soft-btn" id="terminalPin" type="button">'+(pinned.has(selected)?'★ Saved':'☆ Save to watchlist')+'</button><a class="sw-soft-btn" href="'+href+'">Full research ↗</a><a class="sw-soft-btn" href="intelligence.html?ticker='+encodeURIComponent(r.ticker)+'">Intelligence ↗</a></div><p class="sw-meta">'+(valid?'Observed scanner close '+esc(r.date||'date unavailable')+'. Scanner quotes are separate from licensed price histories.':'No scanner price. Reference identity is not a verified active listing.')+'</p><div id="terminalNativeHistory"></div>';
  const news=(signals?.alerts||[]).filter(s=>s.ticker===selected&&newsRelevant(s)).concat((r.stories||[]).filter(newsRelevant));const seen=new Set();
  $('terminalNews').innerHTML=news.filter(s=>safeUrl(s.url)&&!seen.has(s.url)&&seen.add(s.url)).sort((a,b)=>Date.parse(b.published)-Date.parse(a.published)).slice(0,8).map(s=>'<a class="sw-terminal-news" href="'+esc(safeUrl(s.url))+'" target="_blank" rel="noopener noreferrer"><b>'+esc(s.english||s.headline)+'</b><small>'+esc(s.publisher||'Source')+' · '+esc(s.published||'')+'</small></a>').join('')||'<p class="sw-meta">No financially relevant source-linked headlines available for this selection.</p>';
  const native=$('terminalNativeHistory'),g=++gen;
  const entry=(licensedPrices?.records||[]).find(p=>p.listingId===selected&&p.redistributionPermitted===true&&p.priceType==='end_of_day'&&/^data\/licensed-reference-history\/[a-f0-9]{32}\.json$/.test(p.historyPath||''));
  native.textContent='Native equity chart requires authorized dated price observations; no undated sparkline is treated as price history.';
  if(entry)get(entry.historyPath).then(h=>{if(g!==gen||h.listingId!==entry.listingId||h.redistributionPermitted!==true||h.priceType!=='end_of_day'||h.source!==entry.source||h.currency!==entry.currency||h.licenseReference!==entry.licenseReference)return;const p=points((h.bars||[]).map(b=>({date:b.date,value:b.close})));if(p.length>=2)chart(native,[{label:r.name,unit:h.currency,points:p}])}).catch(()=>{});
 }
 function drawSeries(){
  $('terminalSeries').innerHTML=series.map(s=>'<label class="sw-terminal-series"><input type="checkbox" data-terminal-series="'+esc(s.key)+'" '+(keys.includes(s.key)?'checked':'')+'><span><b>'+esc(s.label)+' · '+esc(s.country||'')+'</b><small>'+fmt(s.value)+' '+esc(s.unit)+' · '+esc(s.period||'')+'</small></span></label>').join('')||'<p>No official series available.</p>';
 }
 function drawChart(){
  const selected=keys.map(k=>byKey.get(k)).filter(Boolean);let plotted=[];
  if(mode==='raw'){const s=selected[0];if(s){const a=points(s.history),end=Date.parse(a.at(-1)?.date);plotted=[{...s,points:a.filter(p=>!days||Date.parse(p.date)>=end-days*86400000)}]}}
  else plotted=compareSeries(selected,days);
  root.querySelectorAll('[data-terminal-days]').forEach(b=>{b.classList.toggle('active',+b.dataset.terminalDays===days);b.setAttribute('aria-pressed',String(+b.dataset.terminalDays===days))});
  chart($('terminalChart'),plotted,()=>{days=0;drawChart();save()});
  $('terminalChartSources').innerHTML='<p class="sw-terminal-foot">'+(mode==='raw'?'Original units; first selected series only.':'Common observation dates only · first overlapping date = 100 · no interpolation. Not investment returns.')+'</p>'+plotted.map((s,i)=>'<a class="sw-terminal-source" href="'+esc(safeUrl(s.sourceUrl))+'" target="_blank" rel="noopener noreferrer"><i style="background:'+colors[i]+'"></i>'+esc(s.label)+' · '+esc(s.provider||'Official source')+' ↗</a>').join('');
 }
 $('terminalCommodities').innerHTML=table(['Series','Last','1D'],[...(context?.commodities||[]),...(context?.freight||[])].slice(0,18).map(r=>'<tr><td>'+esc(r.name)+(r.proxy?' <small>ETF proxy</small>':'')+'</td><td>'+fmt(r.last)+'</td><td class="'+tone(r.changePct)+'">'+pct(r.changePct)+'</td></tr>').join(''));
 $('terminalPairs').innerHTML=table(['Pair','A/B','Z'],(context?.shareClasses||[]).map(r=>'<tr><td><a href="spreads.html">'+esc(r.name)+'</a></td><td>'+fmt(r.ratio,4)+'</td><td>'+ (r.stationary?fmt(r.z):'Drift')+'</td></tr>').join(''));
 root.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;
  if(b.dataset.terminalTicker){selected=b.dataset.terminalTicker;drawEquities();drawInstrument();save()}
  if(b.dataset.terminalSector){sector=b.dataset.terminalSector;$('terminalSector').value=sector;drawEquities();save()}
  if(b.id==='terminalPin'){if(pinned.has(selected))pinned.delete(selected);else pinned.add(selected);drawEquities();drawInstrument();save()}
  if(b.dataset.terminalDays!==undefined){days=+b.dataset.terminalDays;drawChart();save()}
  if(b.id==='terminalReset'){try{localStorage.removeItem('stockwatch-terminal-v31')}catch{}location.reload()}
 });
 root.addEventListener('change',e=>{const t=e.target;
  if(t.id==='terminalSector'){sector=t.value;drawEquities();save()}
  if(t.id==='terminalWatch'){watchOnly=t.checked;drawEquities()}
  if(t.id==='terminalMode'){mode=t.value;drawChart();save()}
  if(t.dataset.terminalSeries){const k=t.dataset.terminalSeries;if(t.checked&&keys.length<5)keys.push(k);else if(!t.checked)keys=keys.filter(x=>x!==k);drawSeries();drawChart();save()}
 });
 $('terminalQuery').oninput=e=>{query=e.target.value.trim().toLowerCase();drawEquities()};
 drawEquities();drawSectors();drawInstrument();drawSeries();drawChart();
}
if(typeof module==='object'&&module.exports)module.exports={points,compareSeries,newsRelevant};
else window.StockwatchTerminal={render};
})();
