(()=>{'use strict';
const $=id=>document.getElementById(id),page=document.body.dataset.page;
const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const N=(v,d=2)=>v==null||!Number.isFinite(Number(v))?'—':Number(v).toLocaleString('en-GB',{minimumFractionDigits:0,maximumFractionDigits:d});
const P=v=>v==null||!Number.isFinite(Number(v))?'—':(Number(v)>0?'+':'')+Number(v).toFixed(2)+'%';
const sign=v=>!Number.isFinite(Number(v))||v==null?'sw-neutral':Number(v)>0?'sw-up':Number(v)<0?'sw-down':'sw-neutral';
const link=v=>{try{const u=new URL(v,location.href);return u.protocol==='https:'?u.href:''}catch{return ''}};
const fmtDate=x=>{let d=new Date(x);return !Number.isFinite(d.getTime())?'Unknown':new Intl.DateTimeFormat('en-GB',{timeZone:'UTC',day:'numeric',month:'short',year:'numeric'}).format(d)};
const timeAge=x=>{let n=(Date.now()-Date.parse(x))/3600000;if(!Number.isFinite(n))return 'Unknown';if(n<0)return 'Clock mismatch';return n<2?`${Math.max(1,Math.floor(n*60))} min ago`:n<48?`${Math.floor(n)} hours ago`:`${Math.floor(n/24)} days ago`};
const get=async path=>{const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);try{let r=await fetch(path+(path.includes('?')?'&':'?')+'v='+Date.now(),{cache:'no-store',signal:controller.signal});if(!r.ok)throw new Error(`HTTP ${r.status}: ${path}`);return await r.json()}finally{clearTimeout(timer)}};
const state={signals:null,context:null,watchlist:[],routes:[],health:null,archive:null,fundamentals:{},history:new Map(),missingHistory:new Set(),selection:null,observations:null,identities:null,issuers:null,onboarding:null,researchTargets:null,researchCoverage:null,intelligence:null,referenceDirectory:null,expansion:null,licensedPrices:null,abCandidates:null,chartDisplays:null,events:null};
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
/* Conservative comparison date, not an exchange holiday calendar. */
function comparisonDate(snapshot,now=Date.now()){
 const t=Date.parse(snapshot);if(!Number.isFinite(t))return null;
 const d=new Date(Math.max(t,now));if(d.getUTCHours()<22)d.setUTCDate(d.getUTCDate()-1);
 while(d.getUTCDay()===0||d.getUTCDay()===6)d.setUTCDate(d.getUTCDate()-1);
 return d.toISOString().slice(0,10);
}
function observationQuality(row,target){
 if(!row||row.referenceOnly||row.unavailable||!Number.isFinite(row.close)||row.close<=0||!Number.isFinite(row.changePct))return 'unavailable';
 if(typeof row.date!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(row.date)||!Number.isFinite(Date.parse(row.date))||!target||row.date>target)return 'unconfirmed';
 if(!Number.isFinite(row.volume)||row.volume<0)return 'unconfirmed';
 if(row.priceStatus==='retained')return row.date<target?'older':'unconfirmed';
 if(row.volume===0)return 'no-volume';
 if(row.date<target)return 'older';
 return 'observed';
}
function qualityLabel(q){return ({'no-volume':'No volume',older:'Older price',unconfirmed:'Unconfirmed',unavailable:'No data',observed:'Observed'})[q]||'No data'}
function qualityRows(rows,target){return rows.map(r=>({...r,marketQuality:observationQuality(r,target)}))}
// Display-only: saved same-session observations remain meaningful even when a later refresh fails.
// Strict comparison, alert, ranking and signal paths continue to use observationQuality.
function reportedMapQuality(r,day){
 if(typeof day!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(day)||!Number.isFinite(Date.parse(day))||new Date(day).toISOString().slice(0,10)!==day)return 'unconfirmed';
 if(!r||r.date!==day)return observationQuality(r,day);
 if(r.priceStatus==='retained'&&typeof r.currency==='string'&&r.currency&&Number.isFinite(r.volume)&&r.volume>0&&Number.isFinite(r.close)&&r.close>0&&Number.isFinite(r.changePct)&&!r.referenceOnly&&!r.unavailable)return 'observed';
 return observationQuality(r,day);
}
function reportedMapRows(rows,day){return rows.map(r=>({...r,marketQuality:reportedMapQuality(r,day)}))}
function marketHeatData(all,group='all'){
 return all.filter(x=>x&&!x.referenceOnly&&!x.unavailable&&(!x.marketQuality||x.marketQuality==='observed')&&Number.isFinite(x.close)&&Number.isFinite(x.changePct)&&(group==='all'||x.sector===group));
}
function workspaceHeatmap(all,group='all'){
 const groups=new Map();for(const x of marketHeatData(all,group)){const label=x.sector||'Other';if(!groups.has(label))groups.set(label,[]);groups.get(label).push(x)}
 if(!groups.size)return '<div class="sw-empty">No observed price changes in this selection.</div>';
 return [...groups].sort((a,b)=>b[1].length-a[1].length||a[0].localeCompare(b[0])).map(([label,items])=>'<section class="sw-heat-sector"><h3>'+E(label)+' <small>'+items.length+'</small></h3><div class="sw-heat-cells">'+items.slice().sort((a,b)=>Math.abs(b.changePct)-Math.abs(a.changePct)).map(x=>'<a class="sw-heat-cell '+(x.changePct>0?'positive':x.changePct<0?'negative':'flat')+'" data-strength="'+Math.min(5,Math.ceil(Math.abs(x.changePct)))+'" href="company.html?ticker='+encodeURIComponent(x.ticker)+'" title="'+E(x.name+' · '+P(x.changePct)+(x.date?' · '+x.date:'')+(x.currency?' · '+x.currency:'')+(x.priceStatus==='retained'?' · last saved observation; refresh unavailable':''))+'" aria-label="'+E(x.name+', '+P(x.changePct)+(x.date?', '+x.date:''))+'"><strong>'+E(x.ticker)+'</strong><span>'+E(P(x.changePct))+'</span></a>').join('')+'</div></section>').join('');
}
/* V28: reference coverage does not become market data. */
function displayObservation(r){const q=r?.pairQuote||(!r?.referenceOnly&&!r?.unavailable?r:null);return q&&Number.isFinite(q.close)&&q.close>0&&typeof q.date==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(q.date)&&Number.isFinite(Date.parse(q.date))&&new Date(Date.parse(q.date)).toISOString().slice(0,10)===q.date&&q.currency?q:null}
function coverageHeatRows(all,group='all',coverage='all'){
 return all.filter(x=>(group==='all'||x.sector===group)&&(coverage==='all'||(coverage==='priced'?!!displayObservation(x):coverage==='observed'?marketHeatData([x]).length:!marketHeatData([x]).length)));
}
// Older movements may be displayed, but never counted as the selected session.
function olderMapChange(r,day){
 if(!r||r.referenceOnly||r.unavailable||typeof day!=='string'||typeof r.date!=='string'||r.date>=day||!Number.isFinite(Date.parse(day))||new Date(day).toISOString().slice(0,10)!==day||!Number.isFinite(Date.parse(r.date))||new Date(r.date).toISOString().slice(0,10)!==r.date||!Number.isFinite(r.close)||r.close<=0||typeof r.currency!=='string'||!r.currency||!Number.isFinite(r.volume)||r.volume<=0||!Number.isFinite(r.changePct))return null;
 return {date:r.date,changePct:r.changePct};
}
function pairMapMove(r,day){
 const q=r?.referenceOnly?r.pairQuote:null,m=q?.dailyMove;
 const validDate=d=>typeof d==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d))&&new Date(d).toISOString().slice(0,10)===d;
 if(!m||!displayObservation(r)||!validDate(day)||!validDate(q.date)||q.date>day||!validDate(m.date)||m.date>q.date||(m.date!==q.date&&!(m.saved===true&&Number.isFinite(m.close)&&m.close>0))||!validDate(m.previousDate)||m.method!=='individual_daily_closes'||!Number.isFinite(m.changePct)||m.changePct < -100)return null;
 const prev=new Date(m.date);if(prev.getUTCDay()===0||prev.getUTCDay()===6)return null;
 prev.setUTCDate(prev.getUTCDate()-1);while(prev.getUTCDay()===0||prev.getUTCDay()===6)prev.setUTCDate(prev.getUTCDate()-1);
 return prev.toISOString().slice(0,10)===m.previousDate?m:null;
}
function savedScannerMove(r,day){
 const q=r?.lastValidMovement, dateOK=d=>typeof d==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d))&&new Date(d).toISOString().slice(0,10)===d;
 if(!r||r.referenceOnly||r.unavailable||!q||!displayObservation(r)||!dateOK(day)||!dateOK(r.date)||!dateOK(q.date)||q.date>=r.date||q.date>day||r.date>day||!Number.isFinite(q.close)||q.close<=0||!Number.isFinite(q.volume)||q.volume<=0||!Number.isFinite(q.changePct)||(Number.isFinite(r.volume)&&r.volume>0&&Number.isFinite(r.changePct)))return null;
 return ['ticker','name','currency','exchange','isin','mic'].every(k=>(q[k]??null)===(r[k]??null))?q:null;
}
function neutralMapDetail(r,day,showOlder){
 const q=displayObservation(r),old=showOlder?olderMapChange(r,day):null,pair=showOlder?pairMapMove(r,day):null,saved=showOlder?savedScannerMove(r,day):null;
 if(pair&&q)return '<span class="'+(pair.changePct>0?'sw-up':pair.changePct<0?'sw-down':'sw-neutral')+'">'+E(P(pair.changePct))+' · '+E(pair.date)+'</span><small>'+E((pair.saved?pair.close:q.close).toLocaleString('en-GB',{maximumFractionDigits:3})+' '+q.currency+' · A/B daily move'+(q.retained||pair.saved?' · saved':''))+'</small>'+(pair.date!==q.date?'<small>'+E(q.close.toLocaleString('en-GB',{maximumFractionDigits:3})+' '+q.currency+' · latest price '+q.date)+'</small>':'');
 if(saved&&q)return '<span class="'+(saved.changePct>0?'sw-up':saved.changePct<0?'sw-down':'sw-neutral')+'">'+E(P(saved.changePct))+' · '+E(saved.date)+'</span><small>'+E(saved.close.toLocaleString('en-GB',{maximumFractionDigits:3})+' '+saved.currency+' · saved movement')+'</small><small>'+E(q.close.toLocaleString('en-GB',{maximumFractionDigits:3})+' '+q.currency+' · latest price '+q.date)+'</small>';
 if(old&&q)return '<span class="'+(old.changePct>0?'sw-up':old.changePct<0?'sw-down':'sw-neutral')+'">'+E(P(old.changePct))+' · '+E(old.date)+'</span><small>'+E(q.close.toLocaleString('en-GB',{maximumFractionDigits:3})+' '+q.currency+' · earlier session')+'</small>';
 return '<span>'+E(q?q.close.toLocaleString('en-GB',{maximumFractionDigits:3})+' '+q.currency+' · '+q.date:qualityLabel(r.marketQuality))+'</span>'+(q?'<small>'+E(r.pairQuote?'A/B price only':r.volume===0?'No trading volume':'Change unavailable')+'</small>':'');
}
function coverageHeatmap(rows,day=null,showOlder=false){
 const market=workspaceHeatmap(rows),missing=rows.filter(x=>!marketHeatData([x]).length);
 if(!missing.length)return market;
 const groups=new Map();
 for(const x of missing){const s=x.sector||'Other';if(!groups.has(s))groups.set(s,[]);groups.get(s).push(x)}
 return (marketHeatData(rows).length?market:'')+[...groups].map(([label,items])=>'<section class="sw-heat-sector sw-heat-missing"><h3>'+E(label)+' · dated prices / unavailable changes <small>'+items.length+'</small></h3><div class="sw-heat-cells">'+items.map(x=>'<a class="sw-heat-cell no-data" href="'+(x.registryOnly?'directory.html?q='+encodeURIComponent(x.figi):x.referenceOnly?'company.html?ticker='+encodeURIComponent('ref:'+x.referenceId):'company.html?ticker='+encodeURIComponent(x.ticker))+'" title="'+E(x.name+' · '+qualityLabel(x.marketQuality)+(x.date?' · '+x.date:''))+'"><strong>'+E(x.symbol||x.ticker)+'</strong>'+neutralMapDetail(x,day,showOlder)+'</a>').join('')+'</div></section>').join('');
}
// V68: compact sectors, latest reported date for visualization only.
function screenerHeatRows(rows,reportedDay,strictDay,quality='all'){
 const target=quality==='all'?(reportedDay||strictDay):strictDay;
 return rows.map(r=>({...r,marketQuality:quality==='missing'?'unavailable':quality==='all'?reportedMapQuality(r,target):observationQuality(r,target)}));
}
function compactScreenerHeatmap(rows,day=null,showOlder=false){
 const groups=new Map();for(const x of rows){const sector=x.sector||'Other';if(!groups.has(sector))groups.set(sector,[]);groups.get(sector).push(x)}
 return '<div class="sw-compact-heatgrid">'+[...groups].sort((a,b)=>b[1].length-a[1].length||a[0].localeCompare(b[0])).map(([label,items])=>{
 const count=marketHeatData(items).length;
 const size=items.length>=20?'wide':items.length>=8?'medium':'small';
 return '<section class="sw-compact-heatsector '+size+'"><h3>'+E(label)+' <small>'+count+' / '+items.length+' dated changes'+(showOlder&&items.some(x=>pairMapMove(x,day))?' · '+items.filter(x=>pairMapMove(x,day)).length+' A/B display-only':'')+'</small></h3><div class="sw-heat-cells">'+items.slice().sort((a,b)=>Number(b.marketQuality==='observed')-Number(a.marketQuality==='observed')||Math.abs(b.changePct||0)-Math.abs(a.changePct||0)||String(a.ticker).localeCompare(String(b.ticker))).map(x=>{
 const observed=marketHeatData([x]).length===1,q=displayObservation(x),href=x.registryOnly?'directory.html?q='+encodeURIComponent(x.figi):x.referenceOnly?'company.html?ticker='+encodeURIComponent('ref:'+x.referenceId):'company.html?ticker='+encodeURIComponent(x.ticker);
 const cls=observed?(x.changePct>0?'positive':x.changePct<0?'negative':'flat'):'no-data';
 return '<a class="sw-heat-cell '+cls+'"'+(observed?' data-strength="'+Math.min(5,Math.ceil(Math.abs(x.changePct)))+'"':'')+' href="'+href+'" title="'+E(x.name+' · '+(observed?P(x.changePct):qualityLabel(x.marketQuality))+(q?' · '+q.date:'')+(observed&&x.priceStatus==='retained'?' · last saved observation; refresh unavailable':''))+'"><strong>'+E(x.symbol||x.ticker)+'</strong>'+(observed?'<span>'+E(P(x.changePct))+'</span><small>'+E(q?.date||'')+'</small>':neutralMapDetail(x,day,showOlder))+'</a>';
 }).join('')+'</div></section>'
 }).join('')+'</div>';
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
  if(filters.move!==''&&(r.unavailable||(r.marketQuality&&r.marketQuality!=='observed')||!screenMetric(r.changePct,filters.move,true)))return false;
  if(filters.volume!==''&&(r.unavailable||(r.marketQuality&&r.marketQuality!=='observed')||r.thin||!screenMetric(r.rvol,filters.volume)))return false;
  if(filters.volatility!==''&&(r.referenceOnly||!screenMetric(r.annualVolPct,filters.volatility)))return false;
  if(filters.signal&&(r.unavailable||(r.marketQuality&&r.marketQuality!=='observed')||!(Number.isFinite(r.excessSigma)&&Math.abs(r.excessSigma)>=2||!r.thin&&Number.isFinite(r.rvol)&&r.rvol>=2.5)))return false;
  return true;
 });
}
/* Attention signals are evidence-linked review prompts, not investment advice. */
function stockAttention(rows,stories,now=Date.now()){
 const result=[],seen=new Set(),byTicker=new Map();
 for(const s of stories||[]){
  if(!s||s.duplicateOf||!['strong','mentioned'].includes(s.relevance))continue;
  const stamp=Date.parse(s.published),age=now-stamp;
  if(!Number.isFinite(stamp)||age<0||age>72*3600000)continue;
  let url;try{url=new URL(s.url);if(url.protocol!=='https:')continue}catch{continue}
  const h=String(s.english||s.headline||'').toLowerCase();
  let category=null;
  if(/\b(profit warning|cuts? (?:annual |full.year )?guidance|withdraws? guidance|insolvency|bankruptcy|resultatvarsel)\b/.test(h))category='Financial risk review';
  else if(/\b(ceo|cfo|chief executive|chief financial officer|konsernsjef|finansdirektør|vd)\b/.test(h)&&/\b(resigns?|resignation|steps? down|depart(?:ure|s)|dismiss(?:ed|al)|appoint(?:s|ed|ment)?|replacement|retires?|fratrer|avgår|slutter|utnevner)\b/.test(h))category='Leadership change review';
  else if(/\b(recall|production halt|plant closure|regulatory investigation|export ban)\b/.test(h))category='Operational risk review';
  else if(/\b(awarded|wins contract|order intake|raises? guidance|acquisition|merger)\b/.test(h))category='Material event review';
  if(!category)continue;
  const key=String(s.ticker)+'|'+url.href;if(seen.has(key))continue;seen.add(key);
  const official=s.relevance==='strong'&&s.type==='disclosure'&&s.match==='issuer_code';
  const event={category,official,headline:String(s.headline||s.english||''),url:url.href,published:s.published,publisher:s.publisher||'Source'};
  if(!byTicker.has(s.ticker))byTicker.set(s.ticker,[]);
  byTicker.get(s.ticker).push(event);
 }
 for(const c of rows||[]){
  if(!c||c.referenceOnly)continue;
  const events=(byTicker.get(c.ticker)||[]).sort((a,b)=>Number(b.official)-Number(a.official)||Date.parse(b.published)-Date.parse(a.published));
  const d=Date.parse(c.date),fresh=Number.isFinite(d)&&now>=d&&now-d<=4*86400000;
  const move=!c.unavailable&&fresh&&Number.isFinite(c.close)&&Number.isFinite(c.changePct)&&(Math.abs(c.changePct)>=5||(Number.isFinite(c.excessSigma)&&Math.abs(c.excessSigma)>=2));
  const volume=!c.unavailable&&fresh&&Number.isFinite(c.close)&&!c.thin&&Number.isFinite(c.rvol)&&c.rvol>=2.5;
  if(!events.length&&!move&&!volume)continue;
  result.push({ticker:c.ticker,name:c.name,events,move,volume,changePct:move?c.changePct:null,rvol:volume?c.rvol:null,priceDate:move||volume?c.date:null,rank:(events.some(e=>e.official)?100:events.length?60:0)+(move?20:0)+(volume?10:0)});
 }
 return result.sort((a,b)=>b.rank-a.rank||String(a.ticker).localeCompare(String(b.ticker)));
}
function attentionCard(x){
 const e=x.events[0],label=e?e.category:'Unusual market activity';
 return '<article class="sw-attention-card"><div class="sw-attention-top"><span class="sw-tag '+(e?'':'mint')+'">'+E(label)+'</span><small>'+E(e?(e.official?'Issuer-linked disclosure':'Headline association · review'):'Observed activity')+'</small></div><a class="sw-attention-name" href="company.html?ticker='+encodeURIComponent(x.ticker)+'">'+E(x.name)+' <small>'+E(x.ticker)+'</small></a>'+(e?'<a class="sw-attention-headline" href="'+E(e.url)+'" target="_blank" rel="noopener noreferrer">'+E(e.headline)+'</a><small>'+E(e.publisher)+' · '+E(fmtDate(e.published))+'</small>':'')+'<div class="sw-attention-meta">'+(x.move?'<b class="'+sign(x.changePct)+'">'+P(x.changePct)+'</b>':'')+(x.volume?'<b>'+N(x.rvol,2)+'× relative volume</b>':'')+(x.priceDate?'<small>Price observation '+E(x.priceDate)+'</small>':'')+'</div></article>';
}
/* Homepage uses dated official macro observations, never invented market charts. */
function overviewMacroPoints(series){
 const m=new Map(),bad=new Set();
 for(const x of series?.history||[]){if(!x||typeof x.date!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(x.date)||!Number.isFinite(x.value))continue;
  const t=Date.parse(x.date);if(!Number.isFinite(t)||new Date(t).toISOString().slice(0,10)!==x.date)continue;
  if(m.has(x.date)&&m.get(x.date)!==x.value)bad.add(x.date);else m.set(x.date,x.value);
 }
 return [...m].filter(([k])=>!bad.has(k)).sort(([a],[b])=>a.localeCompare(b)).map(([date,value])=>({date,value}));
}
function renderOverviewEconomicCards(series){
 const root=$('overviewEconomicCards');if(!root)return;
 const chosen=[
 ['fx:EUR/NOK','EUR/NOK','commodities.html'],['fx:USD/NOK','USD/NOK','commodities.html'],
 ['fred:DGS10','US 10-year yield','commodities.html'],['hicp_yoy:NO','Norway inflation','commodities.html'],
 ['fred:INDPRO','US industrial production','terminal.html?research=official'],['hicp_yoy:DE','Germany inflation','commodities.html'],
 ['usda:gulf-japan-index','Gulf–Japan freight index','shipping.html'],['unctad:lsci-monthly:china','China shipping connectivity','shipping.html']];
 const cards=chosen.flatMap(([key,label,href])=>{
  const x=series.find(s=>s.key===key);if(!x||!Number.isFinite(x.value)||typeof x.period!=='string'||!x.unit)return [];
  const points=overviewMacroPoints(x);return ['<a class="sw-economic-card" href="'+href+'"><span>'+E(label)+'</span><strong>'+N(x.value,3)+'</strong><small>'+E(x.unit)+' · '+E(x.period)+'</small>'+(points.length>1?chart(points.slice(-30).map(p=>p.value),150,28):'')+'</a>'];
 });
 root.innerHTML=cards.join('')||'<p class="sw-meta">No official indicators available in the current snapshot.</p>';
}

async function overviewResearch(){
 const host=$('overviewMacro'),catalog=$('overviewDatasetCount');if(!host||!catalog)return;
 const [feeds,inventory,macro,freight,shipping]=await Promise.allSettled([get('data/economic-feeds.json'),get('data/dataset-catalog.json'),get('data/open-data.json'),get('data/shipping-open.json'),get('data/shipping-connectivity.json')]);
 const allSeries=[feeds,macro,freight,shipping].flatMap(x=>x.status==='fulfilled'&&Array.isArray(x.value.series)?x.value.series:[]);
 renderOverviewEconomicCards(allSeries);
 if(inventory.status==='fulfilled'){
  const row=(inventory.value.datasets||[]).find(x=>x.path==='data/free-research.json');
  catalog.textContent=Number.isInteger(row?.records)&&row.records>=0?N(row.records,0)+' official records':'Official datasets';
 }else catalog.textContent='Official datasets unavailable';
 const items=feeds.status==='fulfilled'?(feeds.value.series||[]).filter(x=>['eia:RBRTE','eia:RWTC','fred:DGS10','fred:DGS2','fred:DFF'].includes(x.key)&&overviewMacroPoints(x).length>=2):[];
 if(!items.length){host.innerHTML='<p class="sw-note">Dated official macro history unavailable. <a href="commodities.html">Browse source data ↗</a></p>';return}
 host.innerHTML='<div class="sw-overview-chart-controls"><label>Series <select id="overviewMacroSeries">'+items.map(x=>'<option value="'+E(x.key)+'">'+E(x.label)+'</option>').join('')+'</select></label><label>Range <select id="overviewMacroRange"><option value="90">3 months</option><option value="365">1 year</option><option value="0">All available</option></select></label><label>View <select id="overviewMacroMode"><option value="absolute">Observed value</option><option value="delta">Change from range start</option></select></label></div><div id="overviewMacroPlot"></div>';
 const draw=()=>{
  const item=items.find(x=>x.key===$('overviewMacroSeries').value),all=overviewMacroPoints(item),days=Number($('overviewMacroRange').value),until=Date.parse(all.at(-1).date);
  const p=all.filter(x=>!days||Date.parse(x.date)>=until-days*86400000),last=p.at(-1);
  if(p.length<2){$('overviewMacroPlot').textContent='Insufficient dated observations for this range.';return}
  const delta=$('overviewMacroMode').value==='delta',base=p[0].value,value=x=>delta?x.value-base:x.value;
  const min=Math.min(...p.map(value)),max=Math.max(...p.map(value)),pad=Math.max((max-min)*.07,Math.abs(max)*.005,.0001),lo=min-pad,hi=max+pad;
  const W=640,H=192,L=58,R=14,T=10,B=26,start=Date.parse(p[0].date),end=Date.parse(last.date),X=d=>L+(Date.parse(d)-start)/(end-start||1)*(W-L-R),Y=v=>T+(hi-v)/(hi-lo)*(H-T-B),pts=p.map(x=>X(x.date).toFixed(2)+','+Y(value(x)).toFixed(2)).join(' ');
  const src=link(item.sourceUrl),status=feeds.value.sources?.[item.provider]?.status;
  $('overviewMacroPlot').innerHTML='<div class="sw-overview-chart-value"><strong id="overviewLensValue">'+N(value(last),3)+'</strong><span id="overviewLensDate">'+E(delta?'Change · '+item.unit:item.unit)+' · '+E(last.date)+'</span></div><div id="overviewLensDetail" class="sw-meta" aria-live="polite"></div><svg tabindex="0" viewBox="0 0 640 192" role="img" aria-label="'+E(item.label+' historical observations, '+p[0].date+' to '+last.date)+'" class="sw-overview-chart-svg">'+Array.from({length:4},(_,i)=>{const v=hi-(hi-lo)*i/3,y=Y(v);return '<line x1="'+L+'" x2="'+(W-R)+'" y1="'+y+'" y2="'+y+'" stroke="var(--sw-edge)"/><text x="'+(L-6)+'" y="'+(y+4)+'" text-anchor="end">'+E(N(v,2))+'</text>'}).join('')+'<polyline fill="none" stroke="var(--sw-mint)" stroke-width="2" vector-effect="non-scaling-stroke" points="'+pts+'"/><line id="overviewLensLine" y1="'+T+'" y2="'+(H-B)+'" stroke="var(--sw-muted)" stroke-dasharray="3 3"/><circle id="overviewLensDot" r="4" fill="var(--sw-mint)" stroke="var(--sw-surface)" stroke-width="1.5"/><text x="'+L+'" y="189">'+E(p[0].date)+'</text><text x="'+(W-R)+'" y="189" text-anchor="end">'+E(last.date)+'</text></svg><p class="sw-meta">'+E(p.length+' dated observations · '+(item.provider||'Official source').toUpperCase()+' · '+(status||'status unknown'))+(src?' · <a class="sw-textlink" href="'+E(src)+'" target="_blank" rel="noopener noreferrer">Source ↗</a>':'')+' · Inspect using pointer or arrow keys</p>';
  const svg=$('overviewMacroPlot').querySelector('svg'),line=$('overviewLensLine'),dot=$('overviewLensDot');let at=p.length-1;
  const inspect=i=>{at=Math.max(0,Math.min(p.length-1,i));const q=p[at],x=X(q.date);line.setAttribute('x1',x);line.setAttribute('x2',x);dot.setAttribute('cx',x);dot.setAttribute('cy',Y(value(q)));$('overviewLensValue').textContent=N(value(q),3);$('overviewLensDate').textContent=(delta?'Change · ':'')+item.unit+' · '+q.date;$('overviewLensDetail').textContent='Observed: '+N(q.value,3)+' '+item.unit+' · Δ from '+p[0].date+': '+N(q.value-base,3);};
  const point=e=>{const matrix=svg.getScreenCTM();if(!matrix)return;const q=svg.createSVGPoint();q.x=e.clientX;q.y=e.clientY;const x=q.matrixTransform(matrix.inverse()).x;let nearest=0;for(let i=1;i<p.length;i++)if(Math.abs(X(p[i].date)-x)<Math.abs(X(p[nearest].date)-x))nearest=i;inspect(nearest)};
  svg.addEventListener('pointermove',e=>{if(e.pointerType!=='touch')point(e)});svg.addEventListener('pointerdown',point);svg.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();inspect(e.key==='Home'?0:e.key==='End'?p.length-1:at+(e.key==='ArrowLeft'?-1:1))}});inspect(at);
 };
 $('overviewMacroSeries').onchange=draw;$('overviewMacroRange').onchange=draw;$('overviewMacroMode').onchange=draw;draw();
}

function latestBroadSession(rows,target,minimum=10,displayRetained=false){
 if(typeof target!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(target)||!Number.isFinite(Date.parse(target)))return null;
 const groups=new Map(),seen=new Set();
 for(const r of rows){
  if(!r||(!displayRetained&&r.priceStatus==='retained')||typeof r.ticker!=='string'||seen.has(r.ticker)||typeof r.date!=='string'||r.date>=target||(displayRetained?reportedMapQuality(r,r.date):observationQuality(r,r.date))!=='observed'||new Date(Date.parse(r.date)).toISOString().slice(0,10)!==r.date)continue;
  seen.add(r.ticker);
  if(!groups.has(r.date))groups.set(r.date,[]);
  groups.get(r.date).push({...r,marketQuality:'observed'});
 }
 const day=[...groups.keys()].sort().reverse().find(d=>groups.get(d).length>=minimum);
 if(!day)return null;
 const sample=groups.get(day),sorted=sample.map(r=>r.changePct).sort((a,b)=>a-b),mid=Math.floor(sorted.length/2);
 return {day,rows:sample,median:sorted.length%2?sorted[mid]:(sorted[mid-1]+sorted[mid])/2,up:sample.filter(r=>r.changePct>0).length,down:sample.filter(r=>r.changePct<0).length,flat:sample.filter(r=>r.changePct===0).length};
}

// Latest observed broad date is bounded by the published snapshot, not the
// strict full-session cutoff. This is a dated visualization, never a signal.
function latestBroadReportedSession(rows,snapshot,minimum=10){
 const ts=Date.parse(snapshot);if(!Number.isFinite(ts))return null;
 const end=new Date(ts);end.setUTCHours(0,0,0,0);end.setUTCDate(end.getUTCDate()+1);
 return latestBroadSession(rows,end.toISOString().slice(0,10),minimum,true);
}
// V89b: operational coverage belongs on Data health, not the market homepage.
function renderMarketCoverage(){
 const host=$('marketCoverage');if(!host)return;
 if(!state.signals&&!state.watchlist.length){host.innerHTML='<p class="sw-note">Market coverage unavailable; no counts inferred.</p>';return}
 const target=comparisonDate(state.signals?.generated),listed=qualityRows(companies(),target),universe=qualityRows(directoryRows(),target),valid=listed.filter(x=>!x.unavailable&&Number.isFinite(x.close)),observed=marketHeatData(valid);
 const fallback=observed.length<Math.max(10,Math.ceil(listed.length*.9))?latestBroadReportedSession(listed,state.signals?.generated):null;
 const historical=fallback&&fallback.rows.length>observed.length?fallback:null;
 const displayDate=historical?.day||target,displayUniverse=reportedMapRows(directoryRows(),displayDate);
 const venueCount=new Set(universe.map(x=>x.exchange).filter(Boolean)).size;
  const pricedListings=displayUniverse.filter(displayObservation),movementRows=pricedListings.map(r=>{const move=marketHeatData([r]).length?{date:r.date}:pairMapMove(r,displayDate)||olderMapChange(r,displayDate)||savedScannerMove(r,displayDate);return move}).filter(Boolean);
 const currentMoves=movementRows.filter(x=>x.date===displayDate).length,earlierMoves=movementRows.length-currentMoves;
 host.innerHTML='<section class="sw-overview-coverage" aria-label="Research coverage"><div><span>Priced listings with moves</span><strong class="sw-ws-cover-number">'+N(movementRows.length,0)+' / '+N(pricedListings.length,0)+'</strong><small>Including dated fallbacks</small></div><div><span>Reported · '+E(displayDate||'Unavailable')+'</span><strong>'+N(currentMoves,0)+'</strong><small>Includes A/B display-only</small></div><div><span>Earlier dated moves</span><strong>'+N(earlierMoves,0)+'</strong><small>Not current-session returns</small></div><div><span>Research listings</span><strong>'+N(universe.length,0)+'</strong><small>'+venueCount+' venues · '+listed.length+' monitored</small></div></section>'+
 '<div class="sw-overview-status"><span>Strict scanner comparison · '+E(target||'Unavailable')+': '+observed.length+' / '+listed.length+' comparable equities</span><a class="sw-textlink" href="research.html">Research methodology ↗</a></div>'; 
}
function overview(){
 const target=comparisonDate(state.signals?.generated),listed=qualityRows(companies(),target),universe=qualityRows(directoryRows(),target),references=universe.filter(x=>x.referenceOnly),valid=listed.filter(x=>!x.unavailable&&Number.isFinite(x.close)),observed=marketHeatData(valid),news=storyData();
 const fallback=observed.length<Math.max(10,Math.ceil(listed.length*.9))?latestBroadReportedSession(listed,state.signals?.generated):null;
 const historical=fallback&&fallback.rows.length>observed.length?fallback:null;
 const displayDate=historical?.day||target,displayRows=historical?.rows||observed;const reportedOnly=!!historical;
 const displayUniverse=reportedMapRows(directoryRows(),displayDate);
 const sessionLink=historical?'stocks.html?session='+encodeURIComponent(displayDate):'stocks.html?coverage=monitored';
 const sorted=displayRows.map(x=>x.changePct).sort((a,b)=>a-b),mid=Math.floor(sorted.length/2),median=sorted.length>=10?(sorted.length%2?sorted[mid]:(sorted[mid-1]+sorted[mid])/2):null;
 const qualitySummary=valid.filter(x=>x.marketQuality==='older').length+' older · '+valid.filter(x=>x.marketQuality==='no-volume').length+' zero-volume · '+valid.filter(x=>x.marketQuality==='unconfirmed').length+' unconfirmed';
 const up=displayRows.filter(c=>c.changePct>0).length,down=displayRows.filter(c=>c.changePct<0).length,flat=displayRows.length-up-down;
 const ranked=displayRows.slice().sort((a,b)=>Math.abs(b.changePct)-Math.abs(a.changePct));
 const active=observed.length>=10?observed.filter(c=>Math.abs(c.excessSigma||0)>=2||(c.rvol>=2.5&&!c.thin)).length:null;
 const latest=news.slice().sort((a,b)=>Date.parse(b.published)-Date.parse(a.published)).slice(0,4);
 const sectors=[...new Set(universe.map(x=>x.sector).filter(Boolean))].sort();
 const venues=[...new Set(universe.map(x=>x.exchange).filter(Boolean))].sort(),venueCount=venues.length;
 const pct=n=>displayRows.length?100*n/displayRows.length:0;
 const attention=stockAttention(listed.map(c=>c.marketQuality==='observed'?{...c,excessSigma:observed.length>=10?c.excessSigma:null}:{...c,changePct:null,rvol:null,excessSigma:null}),news);
 const modules=[
 ['equities','Stocks & sectors','Search listings, compare signals and build a watchlist.','stocks.html','▥'],
 ['shipping','Shipping & freight','Global maritime routes and independent voyage models.','shipping.html','⚓'],
 ['energy','Commodities','Energy, metals and macro indicators.','commodities.html','◈'],
 ['energy','Energy intelligence','Explore our connected energy research platform.','https://energy.nordl.dev/','◈'],
 ['research','NVIDIA research','Explore SEC filings and official financial data; no US price feed enabled.','terminal.html?research=official','◇'],
 ['spreads','Share-class spreads','Compare A/B premiums and relative value.','spreads.html','⇌'],
 ['events','Earnings calendar','Upcoming company events and disclosures.','calendar.html','▦'],
 ['news','News & filings','Read chronological source-linked announcements.','news.html','▤'],
 ['compare','Compare stocks','Compare companies side by side.','compare.html','⇄'],
 ['shorts','Short positions','Explore disclosed short positions.','shorts.html','↘'],
 ['research','Data health','Source coverage, timestamps and limitations.','health.html','◉']
 ];
 const pulse=(state.context?.commodities||[]).filter(x=>['Gold','Copper','Brent crude','Natural gas'].includes(x.name)).map(x=>'<a class="sw-ws-pulse" href="commodities.html"><span>'+E(x.name)+'</span><strong>'+N(x.last,3)+' <small>'+E(x.unit||'')+'</small></strong><b class="'+sign(x.changePct)+'">'+P(x.changePct)+'</b></a>').join('');
 const pendingListings=displayUniverse.filter(r=>!r.referenceOnly&&!displayObservation(r));
 const globalPulse=$('globalMarketPulse');if(globalPulse)globalPulse.remove();
 $('v4app').innerHTML=
 '<section class="sw-overview-head"><div><span class="sw-ws-eyebrow">EUROPEAN MARKET INTELLIGENCE</span><h1>Market overview</h1><p>Reported market observations · '+E(displayDate||'Date unavailable')+'</p></div><div class="sw-ws-actions"><a class="sw-primary" href="terminal.html">Open research terminal ↗</a><a class="sw-soft-btn" href="stocks.html">Stock screener</a></div></section>'+
 '<div class="sw-overview-status"><span>Market map, company news and research tools · dated observations</span><a class="sw-textlink" href="health.html">Data health ↗</a></div>'+
 '<div class="sw87-market-grid">'+
 '<section class="sw-panel sw-ws-heatmap">'+panelHeader('Market map','Explore session',sessionLink,E(displayDate||'Date unavailable')+' · equal-size tiles'+(reportedOnly?' · reported observations':''))+'<div class="sw-panel-pad"><div class="sw-ws-heat-toolbar"><label for="workspaceSector">Sector</label><select id="workspaceSector"><option value="all">All sectors</option>'+sectors.map(s=>'<option value="'+E(s)+'">'+E(s)+'</option>').join('')+'</select><label for="workspaceVenue">Trading venue</label><select id="workspaceVenue"><option value="all">All venues</option>'+venues.map(v=>'<option value="'+E(v)+'">'+E(v)+'</option>').join('')+'</select><label for="workspaceCoverage">Coverage</label><select id="workspaceCoverage"><option value="all">All research listings</option><option value="priced" selected>Latest known prices</option><option value="observed">Session observations</option><option value="missing">Older / missing / no volume</option></select><button type="button" id="workspaceHeatExpand" class="sw-soft-btn" aria-expanded="false" aria-controls="workspaceHeatmap">Expand map</button><span id="workspaceHeatCount" aria-live="polite"></span><div class="sw-ws-legend"><span class="sw-down">− Loss</span><span>0% Flat</span><span class="sw-up">+ Gain</span><span>— No data</span></div></div><div id="workspaceHeatmap" class="sw-heatmap-grid" tabindex="0" role="region" aria-label="Scrollable market map"></div>'+(pendingListings.length?'<details id="workspacePending"><summary>'+pendingListings.length+' monitored listing(s) without a valid price</summary><div class="sw-intel-mini">'+pendingListings.map(r=>'<a class="sw-peer" href="company.html?ticker='+encodeURIComponent(r.ticker)+'"><strong>'+E(r.name)+'</strong><small>'+E(r.ticker)+' · price unavailable; collection pending or source unavailable</small></a>').join('')+'</div></details>':'')+'<p class="sw-meta">Reported observation date: '+E(displayDate||'Unavailable')+' · strict comparison session: '+E(target||'Unavailable')+' · saved changes remain dated; never live signals after failed refresh · <a class="sw-textlink" href="health.html">Coverage methodology ↗</a></p></div></section>'+
 '<section class="sw-panel sw-overview-news">'+panelHeader('Latest company intelligence','News & filings','news.html','Source-linked events')+'<div>'+(latest.length?latest.map(storyBrief).join(''):'<div class="sw-empty">No news currently available.</div>')+'</div></section></div>'+
 '<div class="sw87-market-summary">'+
 '<div class="sw-section-row"><h2>Market snapshot</h2><small>'+E(displayDate||'Date unavailable')+' · '+displayRows.length+' comparable observations'+(historical?' · dated reported session; no current signals':'')+'</small></div>'+
 '<div class="sw-ws-metrics">'+stat('Median movement',P(median),E(displayDate||'Date unavailable'),sign(median))+stat('Session listings',N(displayRows.length,0),'Positive-volume observations')+'<article class="sw-card sw-stat sw-ws-breadth"><div class="sw-stat-label">Market breadth</div><div class="sw-ws-breadth-values"><strong class="sw-up">'+up+' up</strong><strong class="sw-down">'+down+' down</strong><span>'+flat+' unchanged</span></div><div class="sw-ws-breadth-bar" aria-label="'+up+' advancing, '+down+' declining, '+flat+' unchanged"><i style="width:'+pct(up)+'%;background:var(--sw-green)"></i><i style="width:'+pct(flat)+'%;background:var(--sw-dim)"></i><i style="width:'+pct(down)+'%;background:var(--sw-red)"></i></div><small>'+E(displayDate||'Date unavailable')+'</small></article></div>'+
 '<div class="sw-two-col"><section class="sw-panel">'+panelHeader('Biggest moves','Explore session',sessionLink,E(displayDate||'Date unavailable'))+'<div>'+moversHtml(top(ranked,7))+'</div></section></div>'+
 '<div class="sw-section-row"><h2>Sector performance</h2><a href="stocks.html" class="sw-textlink">Explore sectors ↗</a></div><div class="sw-sector-grid">'+sectorSummaries(displayRows)+'</div>'+
 '</div>'+
 '<details class="sw-panel sw87-secondary" id="overviewEvents" open><summary>Company events &amp; unusual activity <span>Expand research</span></summary>'+
'<section class="sw-panel sw-attention-panel">'+panelHeader('Stocks needing attention','All company news','news.html','Company events and unusual market activity')+'<div class="sw-attention-grid" tabindex="0" role="region" aria-label="Company attention cards">'+(attention.length?attention.slice(0,6).map(attentionCard).join(''):'<p class="sw-meta">No qualifying recent observations or issuer-linked headlines.</p>')+'</div><p class="sw-meta sw-attention-note">Latest 72h company events · source-linked review prompts</p></section>'+
 '</details>'+
 '<details class="sw-panel sw87-secondary" id="overviewEconomy"><summary>Economic indicators, commodities &amp; shipping <span>Expand charts</span></summary><p class="sw-meta sw87-dataset"><strong id="overviewDatasetCount">Open to load official datasets</strong> · <a class="sw-textlink" href="terminal.html?research=official">Research terminal ↗</a></p>'+
'<div class="sw-section-row"><h2>Market pulse</h2><small>Latest observed data · not live exchange quotes</small></div><div class="sw-ws-pulse-grid">'+(pulse||'<div class="sw-note">Market context unavailable.</div>')+'</div>'+
'<section class="sw-panel sw-economic-dashboard">'+panelHeader('Economic dashboard','All indicators','commodities.html','Rates, currencies, industry and global trade')+'<div id="overviewEconomicCards" class="sw-economic-grid"><p class="sw-meta">Loading official indicators…</p></div></section>'+
 '<div class="sw-overview-workbench"><section class="sw-panel sw-overview-chart">'+panelHeader('Economic indicators','All commodities','commodities.html','Official historical observations · not live quotes')+'<div class="sw-panel-pad" id="overviewMacro"><p class="sw-meta">Loading official history…</p></div></section></div>'+
 '</details>'+
 '<details class="sw-panel sw87-secondary" id="overviewTools"><summary>All research tools &amp; data infrastructure <span>Expand workspace</span></summary>'+
 '<div class="sw-section-row"><h2>Research workspace</h2><small>Specialized tools, common data principles</small></div><div class="sw-ws-modules">'+modules.map(([kind,title,desc,url,ic])=>'<a class="sw-card sw-ws-module" href="'+url+'"><div class="sw-ws-module-art '+kind+'" aria-hidden="true"><span>'+ic+'</span><i></i><i></i><i></i></div><div class="sw-ws-module-text"><h3>'+E(title)+' <span>↗</span></h3><p>'+E(desc)+'</p></div></a>').join('')+'</div>'+
 '<section class="sw-panel sw-ws-trust">'+panelHeader('Trust & data infrastructure','Data health','health.html','Source provenance, freshness and coverage')+'<div class="sw-panel-pad"><div><b>Stockwatch</b><p>Independent market research. Observations can be delayed; missing data is not invented.</p><a class="sw-textlink" href="intelligence.html">Explore connected intelligence ↗</a> <a class="sw-textlink" href="research.html">OpenFIGI integration &amp; historical evidence ↗</a></div><div><b>Leivro</b><p>Our intended central dataset and API platform. Shared infrastructure is being developed.</p><a class="sw-textlink" href="https://leivro.com/">Explore Leivro ↗</a></div></div></section>'+
 '</details>';
 const overview=$('v4app'),marketGrid=overview.querySelector('.sw87-market-grid'),marketSummary=overview.querySelector('.sw87-market-summary');
 if(globalPulse&&marketGrid)marketGrid.before(globalPulse);
 if(marketGrid&&marketSummary){const heading=marketSummary.querySelector('.sw-section-row'),metrics=marketSummary.querySelector('.sw-ws-metrics');if(heading&&metrics){const snapshot=document.createElement('div');snapshot.className='sw87-market-summary sw-overview-priority';snapshot.append(heading,metrics);marketGrid.before(snapshot);}}
 document.body.classList.add('sw-workspace-ready');
 const economy=$('overviewEconomy');let economicStarted=false;
 economy.addEventListener('toggle',()=>{if(!economy.open||economicStarted)return;economicStarted=true;overviewResearch().catch(()=>{if($('overviewMacro'))$('overviewMacro').textContent='Official history unavailable.'})});
 const select=$('workspaceSector'),coverage=$('workspaceCoverage'),venue=$('workspaceVenue'),expand=$('workspaceHeatExpand'),map=$('workspaceHeatmap');
 const draw=()=>{const rows=coverageHeatRows(displayUniverse.filter(r=>venue.value==='all'||r.exchange===venue.value),select.value,coverage.value);map.innerHTML=coverageHeatmap(rows,displayDate,['all','priced'].includes(coverage.value));$('workspaceHeatCount').textContent=rows.length+' listings · '+marketHeatData(rows).length+' with changes'+(['all','priced'].includes(coverage.value)&&rows.some(r=>pairMapMove(r,displayDate))?' · '+rows.filter(r=>pairMapMove(r,displayDate)).length+' A/B display-only':'')};
 for(const control of [select,coverage,venue])control.addEventListener('change',draw);
 expand.addEventListener('click',()=>{const on=map.classList.toggle('sw-heat-expanded');expand.setAttribute('aria-expanded',String(on));expand.textContent=on?'Collapse map':'Expand map'});draw();
}
function instrumentIdentityPanel(t){
 const candidates=(state.identities?.figiCandidates||[]).filter(x=>x.ticker===t);
 const issuers=(state.issuers?.entities||[]).filter(x=>x.ticker===t);
 const one=issuers.length===1?issuers[0]:null,tracked=companies().find(x=>x.ticker===t),refs=(state.researchCoverage?.records||[]).filter(x=>tracked?.mic&&tracked?.isin&&x.mic===tracked.mic&&x.isin===tracked.isin),ref=refs.length===1?refs[0]:null,candidate=candidates.length===1?candidates[0]:candidates.length===0?ref?.currentCandidate:null;
 const fmt=(label,value)=>'<div><small>'+E(label)+'</small><b>'+E(value||'Unavailable')+'</b></div>';
 return '<section class="sw-identity-panel"><div class="sw-section-row"><h2>Instrument identity</h2><a class="sw-textlink" href="https://www.openfigi.com/" target="_blank" rel="noopener noreferrer">OpenFIGI ↗</a></div><p class="sw-meta">Listing-level reference data; FIGI identifiers are candidates unless independently verified. No issuer relationship is inferred from ticker similarity. <a class="sw-textlink" href="research.html">OpenFIGI mapping methodology &amp; historical coverage ↗</a></p><div class="sw-identity-grid">'+fmt('Listing ticker',t)+fmt('ISIN (issuer directory / listing evidence)',one?.isin||tracked?.isin)+fmt('FIGI candidate',candidate?.figi)+fmt('Share-class FIGI candidate',candidate?.shareClassFIGI)+fmt('Composite FIGI candidate',candidate?.compositeFIGI)+fmt('Mapping status',candidates.length>1?'Multiple candidates — unresolved':candidate?'Candidate — not verified':'Not mapped')+'</div>'+(ref?'<p><a class="sw-textlink" href="research.html?instrument='+encodeURIComponent(ref.id)+'&amp;mapping=1#targetDetail">Full reference mapping history ↗</a></p>':'')+'</section>';
}
function sectorChips(items,active,call){return `<div class="sw-filter-row">${['All',...items].map(s=>`<button type="button" data-${call}="${E(s)}" class="${s===active?'active':''}">${E(s)}</button>`).join('')}</div>`}
function renderFacts(c){const f=state.fundamentals?.[c.ticker],m=f?.metrics||{};const keys=[['Market cap','marketCap'],['Revenue','revenue'],['Net income','netIncome'],['Reported operating income','operatingIncome'],['Adjusted operating income','adjustedOperatingIncome'],['Dividend per share','dividendPerShare'],['EPS','eps'],['P/E','pe'],['P/B','pb'],['Dividend yield','dividendYield']];const present=keys.filter(([label,k])=>Number.isFinite(m[k]));if(!present.length)return '<div class="sw-note">Verified earnings and valuation metrics are not yet loaded for this listing. Stockwatch does not estimate or invent missing fundamentals.</div>';return `<div class="sw-section-row"><h2>Verified financial fundamentals</h2><a class="sw-textlink" href="${E(link(f.sourceUrl))}" target="_blank" rel="noopener noreferrer">Original filing ↗</a></div><div class="sw-stat-mini">${present.map(([label,k])=>`<div><small>${E(label)}</small><b>${N(m[k],['revenue','marketCap','netIncome','operatingIncome','adjustedOperatingIncome'].includes(k)?0:2)}${k==='dividendYield'?'%':''}</b></div>`).join('')}</div><p class="sw-meta">${E(f.period||'')} · ${E(f.asOf||'')} · ${E(f.currency||'')} · ${E(f.sourceName||'Original issuer source')}</p>`};
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
// V64: disclosed ownership, not inferred sector exposure.
function reportedInvestments(data){
 const day=d=>typeof d==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d))&&new Date(d).toISOString().slice(0,10)===d;
 const month=d=>typeof d==='string'&&/^\d{4}-(0[1-9]|1[0-2])$/.test(d);
 const sourced=p=>{try{const u=new URL(p.sourceUrl);return u.protocol==='https:'&&u.hostname==='www.wilhelmsen.com'&&!u.username&&!u.password&&typeof p.sourceLocator==='string'&&day(p.publishedOn)&&p.publishedOn<=data.compiledOn}catch{return false}};
 if(data?.schemaVersion!==1||!day(data.compiledOn)||!Array.isArray(data.owners))return [];
 const out=[],seen=new Set();
 for(const o of data.owners){
  if(o?.id!=='wilh-wilhelmsen-holding'||!Array.isArray(o.listingTickers)||o.listingTickers.join(',')!=='WWI.OL,WWIB.OL'||!Array.isArray(o.investments))continue;
  for(const r of o.investments){
   if(!r||typeof r.targetId!=='string'||!r.targetId.match(/^[a-z0-9-]+$/)||typeof r.targetName!=='string'||seen.has(r.targetId)||!['associate','joint_venture'].includes(r.relationship)||!Array.isArray(r.ownership))continue;
   if(r.targetTicker!==null&&({'wallenius-wilhelmsen':'WAWI.OL','reach-subsea':'REACH.OL'})[r.targetId]!==r.targetTicker)continue;
   const ownership=r.ownership.filter(p=>p&&sourced(p)&&(p.precision==='day'?day(p.asOf):p.precision==='month'&&month(p.asOf))&&p.asOf<=p.publishedOn&&Number.isFinite(p.percent)&&p.percent>=0&&p.percent<=100).sort((a,b)=>a.asOf.localeCompare(b.asOf));
   if(!ownership.length||new Set(ownership.map(p=>p.asOf)).size!==ownership.length)continue;
   const financial=p=>p&&sourced(p)&&day(p.periodEnd)&&p.periodEnd<=p.publishedOn&&Number.isFinite(p.usdMillion);
   const profitContribution=(Array.isArray(r.profitContribution)?r.profitContribution:[]).filter(financial).sort((a,b)=>a.periodEnd.localeCompare(b.periodEnd));
   const bookValue=financial(r.bookValue)&&r.bookValue.usdMillion>=0?r.bookValue:null;
   seen.add(r.targetId);out.push({...r,ownerId:o.id,ownerName:o.name,ownerTickers:o.listingTickers,ownership,bookValue,profitContribution});
  }
 }
 return out;
}
function investmentHTML(ticker){
 const rows=reportedInvestments(state.investments).filter(r=>r.ownerTickers.includes(ticker)||r.targetTicker===ticker);
 if(!rows.length)return '';
 return '<section class="sw-panel" data-company-section="ownership"><div class="sw-panel-hd"><div><h2>Disclosed ownership &amp; investment economics</h2><small>Source-linked issuer relationships</small></div></div><div class="sw-panel-pad"><p class="sw-meta">Ownership dates, accounting periods and publication dates are distinct. Profit contributions are reported equity-accounted amounts, not dividends or estimated exposure.</p><div class="sw-intel-mini">'+rows.map(r=>{
 const outgoing=r.ownerTickers.includes(ticker),target=outgoing?r.targetTicker:r.ownerTickers[0],name=outgoing?r.targetName:r.ownerName,last=r.ownership.at(-1),profit=r.profitContribution.at(-1),quote=companies().find(c=>c.ticker===target),rate=outgoing&&r.targetTicker?companyOperatingRows(state.companyOperating,r.targetTicker)[0]?.series.find(v=>v.key==='net_freight'):null,rateLast=rate?.observations.at(-1);
 const href=target&&quote?'company.html?ticker='+encodeURIComponent(target):null;
 return '<article class="sw-peer"><small>'+E(outgoing?r.relationship.replace('_',' '):'Reported investor')+'</small>'+(href?'<a href="'+href+'"><strong>'+E(name)+' ↗</strong></a>':'<strong>'+E(name)+'</strong>')+'<b>'+E(N(last.percent,2))+'% ownership · '+E(last.asOf)+'</b>'+(profit?'<span>Holding share of profit: USD '+E(N(profit.usdMillion,1))+'m · '+E(profit.periodEnd)+'</span>':'')+(r.bookValue?'<span>Holding accounting book value: USD '+E(N(r.bookValue.usdMillion,1))+'m · '+E(r.bookValue.periodEnd)+'</span>':'')+(quote&&Number.isFinite(quote.close)&&quote.date?'<small>Related share price: '+E(N(quote.close,3)+' '+quote.currency+' · '+quote.date)+'</small>':'')+(rateLast?'<small>Investee '+E(rate.label)+': '+E(N(rateLast.value,3)+' '+rate.unit+' · '+rateLast.periodEnd)+'</small><a class="sw-textlink" href="company.html?ticker='+encodeURIComponent(r.targetTicker)+'#issuerOperatingMetrics">Investee freight history ↗</a>':'')+'<a class="sw-textlink" href="'+E(last.sourceUrl)+'" target="_blank" rel="noopener noreferrer">Original disclosure ↗</a><details><summary>Ownership observations</summary>'+r.ownership.map(p=>'<p>'+E(p.asOf)+' · '+E(N(p.percent,2))+'% · published '+E(p.publishedOn)+' · <a href="'+E(p.sourceUrl)+'" target="_blank" rel="noopener noreferrer">'+E(p.sourceLocator)+'</a></p>').join('')+'</details></article>';
 }).join('')+'</div></div></section>';
}
function intelligenceGraph(listings,rules,identities,investments){
 const nodes=new Map(),edges=new Map();
 const node=(id,type,label,extra={})=>{if(!nodes.has(id))nodes.set(id,{id,type,label,...extra});return id};
 const edge=(from,to,type,evidence)=>edges.set(JSON.stringify([from,to,type]),{from,to,type,evidence});
 const config=rules||{};
 const datasets=new Map((config.datasets||[]).map(x=>[x.id,x]));
 const candidates=new Map();
 for(const x of identities?.figiCandidates||[]){if(!candidates.has(x.ticker))candidates.set(x.ticker,[]);candidates.get(x.ticker).push(x)}
 for(const r of listings){
  const id=node('listing:'+r.ticker,'listing',r.name,{ticker:r.ticker,referenceOnly:!!r.referenceOnly,href:r.registryOnly?'directory.html?q='+encodeURIComponent(r.figi):r.referenceOnly?'company.html?ticker='+encodeURIComponent('ref:'+r.referenceId):'company.html?ticker='+encodeURIComponent(r.ticker)});
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
 if(investments)for(const r of reportedInvestments(investments)){
  const issuer=node('issuer:'+r.targetId,'issuer',r.targetName,{href:r.targetTicker&&nodes.has('listing:'+r.targetTicker)?'company.html?ticker='+encodeURIComponent(r.targetTicker):null});
  const last=r.ownership.at(-1),evidence=String(last.percent)+'% reported ownership · '+last.asOf+' · '+last.sourceLocator;
  for(const ticker of r.ownerTickers){const id='listing:'+ticker;if(nodes.has(id))edge(id,issuer,'reported_investment',evidence)}
  if(r.targetTicker&&nodes.has('listing:'+r.targetTicker))edge(issuer,'listing:'+r.targetTicker,'issuer_listing','Explicit investee listing binding');
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
function activeIntelligenceGraph(){return intelligenceGraph(directoryRows(),state.intelligence,state.identities,state.investments)}
function intelligencePanel(c){
 const n=graphNeighborhood(activeIntelligenceGraph(),c.ticker);if(!n)return '';
 return '<section class="sw-intel-summary"><div class="sw-section-row"><h2>Connected intelligence</h2><a class="sw-textlink" href="intelligence.html?ticker='+encodeURIComponent(c.ticker)+'">Explore graph ↗</a></div><p class="sw-meta">Sector-based research context, not proven exposure, correlation or causal relationships.</p><div class="sw-intel-mini">'+(n.context.map(x=>'<a class="sw-peer" href="'+E(x.href)+'"><small>'+E(x.source)+'</small><strong>'+E(x.label)+'</strong><small>Editorial context</small></a>').join('')||'<p class="sw-meta">No curated context links for this sector yet.</p>')+'</div></section>';
}
async function intelligencePage(){
 const root=$('v4app'),graph=activeIntelligenceGraph(),list=graph.nodes.filter(n=>n.type==='listing').sort((a,b)=>a.label.localeCompare(b.label));
 if(!list.length){root.innerHTML='<p class="sw-note">No instrument directory available.</p>';return}
 const p=new URLSearchParams(location.search),selected=list.find(n=>n.ticker===p.get('ticker'))?.ticker||list.find(n=>n.ticker==='FRO.OL')?.ticker||list[0].ticker;
 root.innerHTML='<div class="sw-grid4">'+stat('Listings',N(list.length,0),'Research universe')+stat('Graph nodes',N(graph.nodes.length,0),'Typed reference nodes')+stat('Relationships',N(graph.edges.length,0),'Evidence and context links')+stat('Context series',N(graph.nodes.filter(x=>x.type==='dataset').length,0),'Existing research datasets')+'</div><section class="sw-panel sw-intel-panel">'+panelHeader('Explore connected intelligence','Methodology','research.html','Evidence and editorial context are separate relationship types')+'<div class="sw-panel-pad"><div class="sw-controls"><input id="intelSearch" type="search" aria-label="Filter listings" placeholder="Find a company or ticker"><select id="intelListing" aria-label="Select listing"></select></div><div id="intelMap"></div><div id="intelOwnership"></div><div id="intelData"></div><div id="intelDrivers"></div><div id="intelPeers"></div></div></section>';
 const rel=window.StockwatchRelationships;
 if(rel){const host=document.createElement('div');host.id='commercialNetwork';root.prepend(host);rel.mount(host,state.relationships,{selected:p.get('entity')||rel.entityForListing(state.relationships,p.get('ticker')),review:state.relationshipReview,photos:state.companyPhotos});}
 const us=usSeedRows(state.usSeed);
 if(us.length)root.insertAdjacentHTML('beforeend','<section class="sw-panel" id="usResearch"><div class="sw-panel-hd"><div><h2>US research cohort</h2><small>'+us.length+' SEC-associated US listings · reference only</small></div></div><div class="sw-panel-pad"><p class="sw-meta">Research candidates, not live price coverage. Select a company to open its reference profile and original filings.</p><div class="sw-intel-mini">'+us.map(r=>'<a class="sw-peer" href="company.html?ticker='+encodeURIComponent(r.id)+'"><strong>'+E(r.name)+'</strong><small>'+E(r.exchange+' · '+r.symbol)+'</small><span>'+E(r.group)+'</span></a>').join('')+'</div></div></section>');
 const search=$('intelSearch'),select=$('intelListing');let current=selected;
 function options(){const q=search.value.trim().toLowerCase(),rows=list.filter(n=>(n.label+' '+n.ticker).toLowerCase().includes(q));select.innerHTML=rows.map(n=>'<option value="'+E(n.ticker)+'">'+E(n.label+' · '+n.ticker.replace(/^ref:/,''))+'</option>').join('');if(rows.some(x=>x.ticker===current))select.value=current;else if(rows.length)current=rows[0].ticker;return rows.length}
 let generation=0;
 async function draw(){
  const version=++generation,n=graphNeighborhood(graph,current);
  if(!n||!select.options.length){$('intelMap').innerHTML='<p class="sw-note">No matching listings.</p>';$('intelOwnership').textContent='';$('intelData').textContent='';$('intelDrivers').textContent='';$('intelPeers').textContent='';return}
  if(window.StockwatchIndustry)window.StockwatchIndustry.mount($('intelDrivers'),{config:state.intelligence,sector:n.direct.find(x=>x.type==='sector')?.label,ticker:current,load:get});
  const branch=(x)=>'<div class="sw-intel-node"><small>'+E(x.type==='identifier'?'Unverified candidate':x.type==='sector'?'Editorial sector':x.type==='issuer'?'Reported investment':'Directory venue')+'</small>'+(x.href?'<a href="'+E(x.href)+'"><strong>'+E(x.label)+'</strong></a>':'<strong>'+E(x.label)+'</strong>')+'<span>'+E(x.evidence)+'</span></div>';
  $('intelMap').innerHTML='<div class="sw-intel-map"><div class="sw-intel-center"><small>'+E(n.center.referenceOnly?'REFERENCE ONLY':'MONITORED LISTING')+'</small><a href="'+E(n.center.href)+'"><strong>'+E(n.center.label)+'</strong></a><span>Selected instrument record</span></div><div class="sw-intel-connector" aria-hidden="true"></div><div class="sw-intel-branches">'+n.direct.map(branch).join('')+'</div></div><p class="sw-meta">Listed venue does not identify company domicile. Shared classifications and identifier candidates do not establish corporate ownership or verified economic links.</p>';
  $('intelOwnership').innerHTML=investmentHTML(current);
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
/* V30b — explicitly mapped, display-only third-party charts. */
function displayChartMapping(id,registry){
 const r=(registry?.records||[]).find(x=>x.listingId===id);
 if(!r||!['embed','external'].includes(r.mode)||!/^(OMXSTO|OMXHEX|OMXCOP|OSL):[A-Z0-9_]+$/.test(r.symbol))return null;
 if(r.mode==='embed'&&r.symbol.startsWith('OSL:'))return null;
 const url='https://www.tradingview.com/symbols/'+r.symbol.replace(':','-')+'/';
 return {...r,url};
}
function tvChartOptions(symbol,theme,style='1'){
 const dark=theme!=='light';
 return {symbol,autosize:true,interval:'D',timezone:'Europe/Oslo',theme:dark?'dark':'light',style:style==='3'?'3':'1',locale:'en',backgroundColor:dark?'#101b2c':'#ffffff',gridColor:dark?'rgba(141,160,188,0.10)':'rgba(88,109,138,0.12)',allow_symbol_change:false,hide_side_toolbar:true,hide_top_toolbar:false,hide_legend:false,hide_volume:false,withdateranges:true,save_image:false,calendar:false,details:false,hotlist:false,studies:[],watchlist:[],compareSymbols:[]};
}
function displayChartCard(row){
 const m=displayChartMapping(row.ticker,state.chartDisplays);
 if(!m)return '';
 return '<section class="sw-tv-card" data-tv-listing="'+E(row.ticker)+'"><div class="sw-tv-heading"><div><span class="sw-ws-eyebrow">External market chart</span><h2>'+E(row.name)+'</h2><p class="sw-meta">'+E(m.symbol)+' · Provider-supplied price display</p></div><a class="sw-soft-btn" href="'+E(m.url)+'" target="_blank" rel="noopener noreferrer nofollow">Open TradingView ↗</a></div>'+(m.mode==='embed'?'<div class="sw-tv-controls"><button class="sw-primary" type="button" data-tv-load>Load interactive chart</button><label>Chart type <select data-tv-style aria-label="Chart type"><option value="1">Candlesticks</option><option value="3">Line</option></select></label></div><div class="sw-tv-frame" data-tv-frame hidden></div><p data-tv-status class="sw-meta" role="status">Loading connects your browser to TradingView. The chart may be delayed or unavailable for individual symbols.</p>':'<p class="sw-note">Oslo is not listed in the provider’s free widget market coverage. Open the exact instrument on TradingView instead.</p>')+'<p class="sw-meta">TradingView data is display-only and is not imported into Stockwatch history, screening, or the A/B calculations. Native licensed history is shown separately when available.</p></section>';
}
function loadDisplayChart(card){
 const r=displayChartMapping(card.dataset.tvListing,state.chartDisplays),frame=card.querySelector('[data-tv-frame]'),status=card.querySelector('[data-tv-status]');
 if(!r||r.mode!=='embed'||!frame||!status)return;
 frame.hidden=false;frame.replaceChildren();card.dataset.tvLoaded='true';
 const host=document.createElement('div');host.className='tradingview-widget-container';
 const plot=document.createElement('div');plot.className='tradingview-widget-container__widget';
 const credit=document.createElement('div');credit.className='tradingview-widget-copyright';
 const link=document.createElement('a');link.href=r.url;link.target='_blank';link.rel='noopener nofollow';link.textContent=r.symbol+' chart';
 const attribution=document.createElement('span');attribution.className='trademark';attribution.textContent=' by TradingView';
 credit.append(link,attribution);
 const script=document.createElement('script');script.src='https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';script.async=true;script.type='text/javascript';
 script.textContent=JSON.stringify(tvChartOptions(r.symbol,document.body.dataset.theme,card.querySelector('[data-tv-style]').value));
 status.textContent='Third-party chart requested. If unavailable, use the TradingView link above.';
 script.onerror=()=>{if(host.isConnected)status.textContent='The chart script could not load. Use the TradingView link or retry.'};
 host.append(plot,credit,script);frame.append(host);
 card.querySelector('[data-tv-load]').textContent='Reload chart';
}
function wireDisplayCharts(){
 document.addEventListener('click',e=>{const b=e.target.closest?.('[data-tv-load]');if(b)loadDisplayChart(b.closest('.sw-tv-card'))});
 document.addEventListener('change',e=>{if(e.target.matches('[data-tv-style]')){const c=e.target.closest('.sw-tv-card');if(c?.dataset.tvLoaded==='true')loadDisplayChart(c)}});
 new MutationObserver(()=>document.querySelectorAll('.sw-tv-card[data-tv-loaded="true"]').forEach(loadDisplayChart)).observe(document.body,{attributes:true,attributeFilter:['data-theme']});
}
function displayChartLink(row){
 const m=displayChartMapping(row.ticker,state.chartDisplays);
 return m&&row.referenceOnly?' <a class="sw-row-action sw-tv-link" href="'+licensedHistoryUrl(row.ticker)+'">'+(m.mode==='embed'?'Chart ↗':'Price source ↗')+'</a>':'';
}
function licensedReferenceRows(index,universe){
 const ids=new Map(universe.filter(r=>r.referenceOnly).map(r=>[r.ticker,r]));
 const valid=new Map();
 for(const p of index?.records||[]){
  if(!ids.has(p.listingId)||(p.publicDisplayPermitted!==true&&(p.publicDisplayPermitted!==undefined||p.redistributionPermitted!==true))||p.priceType!=='end_of_day'||!Number.isFinite(p.close)||p.close<=0||!Number.isFinite(p.changePct)||!/^\d{4}-\d{2}-\d{2}$/.test(p.lastDate||'')||!/^data\/licensed-reference-history\/[a-f0-9]{32}\.json$/.test(p.historyPath||'')||!p.source||!p.licenseReference||!p.currency)continue;
  valid.set(p.listingId,p);
 }
 return valid;
}
function licensedReferenceCount(universe){return licensedReferenceRows(state.licensedPrices,universe).size}
function licensedHistoryUrl(id){return 'price-history.html?listing='+encodeURIComponent(id)}
async function licensedPricePage(){
 const root=$('v4app'),universe=directoryRows(),prices=licensedReferenceRows(state.licensedPrices,universe);
 const sourceConfig=await get('data/delayed-exchange-sources.json').catch(()=>null);
 const officialSources='<section class="sw-panel"><div class="sw-panel-pad"><h2>Official delayed exchange sources</h2><p class="sw-meta">15-minute delayed trade reports, not licensed stock closing prices. No public price publication is enabled.</p><div class="sw-intel-mini">'+(sourceConfig?.sources||[]).map(s=>'<div class="sw-peer"><strong>'+E(s.name)+'</strong><small>'+E(s.markets.join(' · '))+'</small><span>'+E(s.collection)+'</span><small>'+E(s.publicDisplay)+'</small><a class="sw-textlink" href="'+E(link(s.url))+'" target="_blank" rel="noopener noreferrer">Official report portal ↗</a></div>').join('')+'</div></div></section>';
 const priority=(state.researchCoverage?.records||[]).filter(r=>r.mic==='XOSL'&&r.isin);
 const priorityPanel='<section class="sw-panel" id="pricePriority"><div class="sw-panel-pad"><h2>Oslo price onboarding priorities</h2><p class="sw-meta">Exchange-sourced ISINs. Mapping status is OpenFIGI candidate evidence, not a confirmed match to a trade or publication permission. Existing price coverage is unchanged.</p><div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Listing</th><th>ISIN</th><th>Identity evidence</th><th>Price history</th></tr></thead><tbody>'+priority.map(r=>'<tr><td>'+E(r.name)+' <small>'+E(r.symbol)+'</small></td><td>'+E(r.isin)+'</td><td>'+E(r.mappingStatus)+'</td><td><a class="sw-textlink" href="'+licensedHistoryUrl('ref:'+r.id)+'">'+(prices.has('ref:'+r.id)?'Licensed EOD history':'Awaiting licensed prices')+' ↗</a></td></tr>').join('')+'</tbody></table></div></div></section>';
 const requested=new URLSearchParams(location.search).get('listing');
 const row=universe.find(x=>x.ticker===requested),q=prices.get(requested);
 if(requested&&!row){root.innerHTML='<div class="sw-note">Unknown research listing. <a href="stocks.html">Open stocks directory ↗</a></div>';return}
 const linkTo=(r,p)=>'<tr><td><a class="sw-textlink" href="'+licensedHistoryUrl(r.ticker)+'">'+E(r.name)+'</a></td><td>'+E(p.currency)+' '+E(N(p.close,4))+'</td><td>'+E(p.lastDate)+'</td><td>'+E(p.source)+'</td></tr>';
 const monitored=companies().filter(c=>window.StockwatchScreener?.hasPrice(c)).sort((a,b)=>a.name.localeCompare(b.name));
 const monitoredRows=monitored.map(c=>'<tr><td><a class="sw-textlink" href="company.html?ticker='+encodeURIComponent(c.ticker)+'">'+E(c.name)+'</a><small>'+E(c.ticker)+'</small></td><td><strong>'+E(N(c.close,4))+' '+E(c.currency)+'</strong></td><td>'+E(c.date)+(c.priceStatus==='retained'?' · last saved':'')+'</td></tr>').join('');
 const monitoredPanel='<section class="sw-panel"><div class="sw-panel-hd"><h2>Latest saved stock prices</h2><small>'+monitored.length+' monitored listings</small></div><div class="sw-panel-pad"><p class="sw-meta">Existing scanner observations from the Stockwatch watchlist, dated and retained when recent refresh is unavailable. These are not separately licensed historical series, real-time exchange quotes, or permission to redistribute vendor files. Select a company for its research profile.</p><div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Company</th><th>Last observed price</th><th>Observation date</th></tr></thead><tbody>'+monitoredRows+'</tbody></table></div></div></section>';
 if(!requested){root.innerHTML='<div class="sw-grid4">'+stat('Latest stock prices',monitored.length,'Existing dated scanner observations')+stat('Licensed EOD archives',prices.size,'Separately licensed historical series')+stat('Research universe',universe.length,'Listings, not unique issuers')+'</div>'+monitoredPanel+'<section class="sw-panel">'+panelHeader('Licensed price coverage','Stocks directory','stocks.html','Daily closes, not live quotes')+'<div class="sw-panel-pad">'+(prices.size?'<div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Listing</th><th>Last close</th><th>Session date</th><th>Source</th></tr></thead><tbody>'+universe.filter(r=>prices.has(r.ticker)).map(r=>linkTo(r,prices.get(r.ticker))).join('')+'</tbody></table></div>':'<p>No licensed reference price series have been imported. Provider permissions and reviewed instrument mappings are required.</p>')+'</div></section>'+officialSources+priorityPanel;return}
 root.innerHTML='<section class="sw-panel"><div class="sw-panel-pad"><h2>'+E(row.name)+'</h2><p class="sw-meta">'+E(row.symbol||row.ticker)+' · '+E(row.exchange||'')+' · End-of-day history</p>'+displayChartCard(row)+'<div id="licensedSeries"></div><p><a class="sw-textlink" href="stocks.html">All research listings ↗</a> · <a class="sw-textlink" href="research.html">Source methodology ↗</a></p></div></section>';
 const target=$('licensedSeries');
 if(!q){const venue=['XOSL','XPAR','XAMS','XBRU','XDUB','XLIS','XMIL'].includes(row.mic)&&/^[A-Z]{2}[A-Z0-9]{9}[0-9]$/.test(row.isin||'')?'https://live.euronext.com/en/product/equities/'+encodeURIComponent(row.isin)+'-'+encodeURIComponent(row.mic):null;target.innerHTML='<div class="sw-note">A separately licensed daily close is not connected for this listing.'+(venue?' <a class="sw-textlink" href="'+E(venue)+'" target="_blank" rel="noopener noreferrer">View the official Euronext quote ↗</a>':'')+'</div>';return}
 const d=await get(q.historyPath).catch(()=>null);
 if(!d||d.listingId!==q.listingId||(d.publicDisplayPermitted!==true&&(d.publicDisplayPermitted!==undefined||d.redistributionPermitted!==true))||d.priceType!=='end_of_day'||d.currency!==q.currency||d.source!==q.source||d.licenseReference!==q.licenseReference||!Array.isArray(d.bars)){target.innerHTML='<div class="sw-note">Licensed history unavailable or inconsistent.</div>';return}
 const bars=d.bars.filter(x=>Number.isFinite(x.close)&&x.close>0).map(x=>({date:x.date,value:x.close}));
 target.innerHTML='<div class="sw-history-source"><strong>'+E(q.source)+'</strong><span>'+E(q.currency)+' · '+(d.adjusted?'Adjusted':'Unadjusted')+' closes · '+E(q.lastDate)+'</span><a class="sw-textlink" href="'+E(link(d.sourceUrl))+'">Source ↗</a> <a class="sw-textlink" href="'+E(link(d.licenseReference))+'">Licence ↗</a></div>'+lineGraph(bars,{label:row.name+' · licensed EOD close',unit:q.currency})+'<p class="sw-meta">Change is between consecutive recorded closes; missing sessions are not filled. These observations are separate from the legacy scanner signals.</p>';
}
function directoryRows(){
 const base=researchUniverse(companies(),state.researchTargets,state.researchCoverage);
 return [...base,...referenceCatalogRows(state.expansion).map(x=>({...x,expandedReference:true}))].map(r=>{const pairQuote=window.StockwatchScreener?.pairQuote(r,state.context?.shareClasses);return pairQuote?{...r,pairQuote,currency:pairQuote.currency}:r});
}
function quickMatches(rows,query){
 const q=query.trim().toLowerCase();if(!q)return [];
 return rows.map(r=>{const symbol=String(r.symbol||r.ticker).toLowerCase(),name=String(r.name||'').toLowerCase(),id=String(r.figi||'').toLowerCase(),base=symbol.split('.')[0],isin=String(r.isin||'').toLowerCase();return {r,score:symbol===q||id===q||base===q||isin===q?0:name===q?1:symbol.startsWith(q)?2:name.startsWith(q)?3:[name,symbol,id,r.isin||''].join(' ').toLowerCase().includes(q)?4:99}}).filter(x=>x.score<99).sort((a,b)=>a.score-b.score||Number(!!a.r.referenceOnly)-Number(!!b.r.referenceOnly)||a.r.name.localeCompare(b.r.name)).slice(0,7).map(x=>x.r);
}
function wireQuickSearch(){
 const input=$('swGlobalSearch'),form=$('swSearchForm');if(!input||!form)return;
 const box=document.createElement('div');box.className='sw-quick-results';box.hidden=true;box.id='swQuickResults';form.appendChild(box);input.setAttribute('aria-controls',box.id);input.setAttribute('autocomplete','off');
 const rows=directoryRows();
 function draw(){const q=input.value.trim(),matches=quickMatches(rows,q);box.hidden=!q;if(!q){box.innerHTML='';return}box.innerHTML=matches.map(r=>'<a href="'+(r.registryOnly?'directory.html?q='+encodeURIComponent(r.figi):r.referenceOnly?'company.html?ticker='+encodeURIComponent('ref:'+r.referenceId):'company.html?ticker='+encodeURIComponent(r.ticker))+'"><strong>'+E(r.name)+'</strong><small>'+E(r.symbol||r.ticker)+' · '+E(r.exchange||'')+' · '+(r.referenceOnly?'Reference only':'Monitored')+'</small></a>').join('')+'<a class="sw-quick-all" href="stocks.html?q='+encodeURIComponent(q)+'">Search all research listings ↗</a><a class="sw-quick-all" href="search.html?q='+encodeURIComponent(q)+'">Search companies, news and datasets ↗</a><a class="sw-quick-all" href="stocks.html?universe=registry&amp;q='+encodeURIComponent(q)+'">Search full OpenFIGI catalog ↗</a>'}
 input.addEventListener('input',draw);input.addEventListener('focus',draw);form.addEventListener('keydown',e=>{if(e.key==='Escape'){box.hidden=true;input.focus()}if(e.key==='ArrowDown'&&e.target===input&&!box.hidden){e.preventDefault();box.querySelector('a')?.focus()}});document.addEventListener('click',e=>{if(!form.contains(e.target))box.hidden=true});
}
function stocks(){const registryMode=new URLSearchParams(location.search).get('universe')==='registry';let all=registryMode?referenceCatalogRows(state.referenceDirectory):directoryRows(),sect=[...new Set(all.map(c=>c.sector).filter(Boolean))].sort(),ex=[...new Set(all.map(c=>c.exchange).filter(Boolean))].sort(),params=new URLSearchParams(location.search);const currentSession=comparisonDate(state.signals?.generated),reported=registryMode?null:latestBroadReportedSession(directoryRows(),state.signals?.generated),historical=registryMode?null:reported&&(reported.day!==currentSession||reported.rows.some(r=>r.priceStatus==='retained'))?reported:latestBroadSession(directoryRows(),currentSession),historicalMode=!!historical&&params.get('session')===historical.day;
all=historicalMode?qualityRows(historical.rows.map(c=>({...c,excessSigma:null})),currentSession):qualityRows(all,currentSession);
const screen=window.StockwatchScreener,session=historicalMode?historical.day:currentSession,currencies=[...new Set(all.map(c=>c.currency).filter(Boolean))].sort();const licensed=historicalMode?new Map():licensedReferenceRows(state.licensedPrices,all);let chosen=sect.includes(params.get('sector'))?params.get('sector'):'All';let q=params.get('q')||'',sort='abs';let favoriteOnly=false;let currentPage=1;const pageSize=50;let favs;try{favs=new Set(JSON.parse(localStorage.getItem('stockwatch-v4-favorites')||'[]'))}catch{favs=new Set()};
$('v4app').innerHTML=`<div class="sw-screener-head"><div><span class="sw-ws-eyebrow">MARKET WORKSPACE</span><h2>${historicalMode?'Dated stock screener':'Stock screener'}</h2><p class="sw-meta">${historicalMode?'Reported observations · '+E(historical.day)+' · no current signals': 'Current comparison session · '+E(currentSession||'Unavailable')}</p></div><div class="sw-controls">${historical?'<a class="sw-soft-btn '+(historicalMode?'':'active')+'" href="stocks.html?coverage=monitored">Latest session</a><a class="sw-soft-btn '+(historicalMode?'active':'')+'" href="stocks.html?session='+encodeURIComponent(historical.day)+'">'+E(historical.day)+' · reported</a>':''}</div></div><div id="stkViewControls" class="sw-controls sw51-views sw86-view-controls"><span class="sw-meta">Display</span><button type="button" class="sw-soft-btn active" data-stk-view="table" aria-pressed="true">Table</button><button type="button" class="sw-soft-btn" data-stk-view="heat" aria-pressed="false">Sector heatmap</button><a class="sw-textlink" href="#stkResults">Go to results ↓</a></div><div class="sw-grid4">${stat(registryMode?'OpenFIGI registry':'Research universe',N(all.length,0),registryMode?'Venue reference records':'Monitored + reference listings')}${stat('Comparable session',N(all.filter(c=>screen?.comparable(c,session)).length,0),session||'Session unavailable')}${stat('Listings with prices',N(all.filter(c=>!!screen?.displayPrice(c)||licensed.has(c.ticker)).length,0),N(all.filter(c=>!screen?.displayPrice(c)&&!licensed.has(c.ticker)).length,0)+' without prices')}${stat('Exchanges',N(ex.length,0),'Trading venues')}</div><div class="sw-controls sw-universe-switch"><a class="sw-soft-btn ${registryMode?'':'active'}" href="stocks.html">Curated research universe · ${N(directoryRows().length,0)}</a><a class="sw-soft-btn ${registryMode?'active':''}" href="stocks.html?universe=registry">OpenFIGI reference catalog · ${state.referenceDirectory?N(state.referenceDirectory.records?.length||0,0):'Unavailable'}</a></div><p class="sw-meta">These are separate views, not additive counts. The expanded Nordic discovery selection uses collected OpenFIGI records, excluding known share-class and symbol overlaps; active or primary listing status still requires verification. Licensed end-of-day imports, when available, are labelled and kept separate from scanner calculations. <a class="sw-textlink" href="price-history.html">Historical coverage ↗</a></p><div class="sw-controls"><input type="search" id="stkSearch" placeholder="Search companies or tickers" value="${E(q)}"><select id="stkExchange"><option value="all">All exchanges</option>${ex.map(x=>`<option value="${E(x)}">${E(x)}</option>`).join('')}</select><select id="stkCoverage" aria-label="Price coverage"><option value="priced">Listings with prices</option><option value="all">All research listings</option><option value="monitored">Monitored stocks</option><option value="reference">Instrument directory · no quotes</option></select><select id="stkCurrency" aria-label="Currency"><option value="all">All currencies</option>${currencies.map(x=>`<option value="${E(x)}">${E(x)}</option>`).join('')}</select><select id="stkSessionQuality" aria-label="Session coverage"><option value="all">All data quality</option><option value="comparable">Comparable session only</option><option value="missing">Missing or different session</option></select><select id="stkSort"><option value="abs">Biggest moves</option><option value="gain">Top gainers</option><option value="loss">Top losers</option><option value="volume">Relative volume</option><option value="name">Company name</option><option value="volatility">Watchlist selection volatility</option></select><button id="favoriteOnly" class="sw-soft-btn" type="button" aria-pressed="false">☆ My watchlist</button></div><div class="sw-controls sw-screen-presets" ${registryMode?'hidden':''}><span class="sw-meta">Quick screens</span><button class="sw-soft-btn" data-screen="all" type="button">All listings</button><button class="sw-soft-btn" data-screen="moves" type="button">Moves ≥ 3%</button><button class="sw-soft-btn" data-screen="volume" type="button">Volume ≥ 2.5×</button><button class="sw-soft-btn" data-screen="signals" type="button">Unusual activity</button></div><details class="sw-panel sw-advanced-filters" ${registryMode?'hidden':''}><summary>Advanced price &amp; activity filters</summary><div class="sw-controls"><label>Min absolute 1D move (%)<input id="stkMove" type="number" min="0" step="0.1" placeholder="Any"></label><label>Min relative volume (×)<input id="stkVolume" type="number" min="0" step="0.1" placeholder="Any"></label><label>Min selection volatility (%)<input id="stkVolatility" type="number" min="0" step="1" placeholder="Any"></label><label class="sw-check-filter"><input id="stkSignal" type="checkbox"> Unusual activity only</label><button id="stkResetMetrics" class="sw-soft-btn" type="button">Clear metrics</button></div><p class="sw-meta">Missing values do not pass numeric filters. Thin listings are excluded from relative-volume filters. Selection volatility is the watchlist screening statistic, not a fresh rolling calculation. Relative-volume signals use the existing scanner thresholds.</p></details><p class="sw-meta sw-directory-note">Reference listings are searchable alongside monitored securities; they do not contribute to market breadth, price signals or returns. <a class="sw-textlink" href="research.html">Identity evidence &amp; historical coverage ↗</a></p><section id="stkResults" class="sw-panel sw51-screener">${sectorChips(sect,chosen,'sector')}<div class="sw-panel-hd"><h2>${historicalMode?'Dated session listings':'Company directory'}</h2><small id="stockCount"></small></div><div class="sw-controls sw51-result-tools"><a class="sw-textlink" href="#stkViewControls">↑ View options / filters</a><details class="sw51-columns"><summary>Columns</summary><div id="stkColumns"></div></details></div><p class="sw-meta sw51-note">Latest reported prices and dated changes are shown when available. Rankings use the strict comparison session. The heatmap defaults to the latest broadly reported date; explicit session filters retain their meaning. No live-price guarantee.</p><div id="stkHeat" hidden></div><div id="stkTable" class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Company</th><th>Exchange</th><th>Last price</th><th>30D trend</th><th>${historicalMode?'Reported 1D change':'1D change'}</th><th>Relative volume</th><th></th></tr></thead><tbody id="stocksRows"></tbody></table></div><div class="sw-ws-pagination"><button id="stockPrev" class="sw-soft-btn" type="button">← Previous</button><span id="stockPage" aria-live="polite"></span><button id="stockNext" class="sw-soft-btn" type="button">Next →</button></div></section><div id="stockDetail"></div>${onboardingPanel()}`;
let view='table';const colLabels=['Company','Exchange','Last price','30D trend','1D change','Relative volume','Research'];let hiddenCols=[];try{const saved=JSON.parse(localStorage.getItem('stockwatch-v51-columns')||'[]');if(Array.isArray(saved))hiddenCols=saved.filter(n=>Number.isInteger(n)&&n>=1&&n<=5)}catch{}$('stkColumns').innerHTML=colLabels.map((label,n)=>n===0||n===6?'':'<label><input type="checkbox" data-stk-column="'+n+'" '+(!hiddenCols.includes(n)?'checked':'')+'>'+E(label)+'</label>').join('');function columns(){document.querySelectorAll('#stkTable tr').forEach(row=>[...row.children].forEach((cell,n)=>{if(cell.colSpan===1)cell.hidden=hiddenCols.includes(n)}))}function draw(){const query=$('stkSearch').value.trim().toLowerCase(),exchange=$('stkExchange').value,coverage=$('stkCoverage').value;let a=screenFinancialRows(all.filter(c=>(coverage==='all'||(coverage==='priced'?!!screen?.displayPrice(c)||licensed.has(c.ticker):coverage==='reference'?c.referenceOnly&&!screen?.displayPrice(c)&&!licensed.has(c.ticker):!c.referenceOnly))&&(chosen==='All'||c.sector===chosen)&&(exchange==='all'||c.exchange===exchange)&&(!favoriteOnly||favs.has(c.ticker))&&(!query||`${c.name} ${c.symbol||c.ticker} ${c.sector} ${c.isin||''} ${c.figi||''} ${c.mic||''}`.toLowerCase().includes(query))),{move:$('stkMove').value,volume:$('stkVolume').value,volatility:$('stkVolatility').value,signal:$('stkSignal').checked});
if(screen){a=screen.filters(a,{session,currency:$('stkCurrency').value,coverage:$('stkSessionQuality').value});a=screen.rank(a,$('stkSort').value,session)}else a.sort((x,y)=>x.name.localeCompare(y.name));$('stkHeat').innerHTML=view==='heat'?(a.length?'<p class="sw-meta sw-heat-date">Map observation date: '+E($('stkSessionQuality').value==='all'?(historicalMode?session:reported?.day||session):session||'Unavailable')+' · '+($('stkSessionQuality').value==='all'?'reported changes; not strict signals':'selected strict-session filter')+'</p>'+compactScreenerHeatmap(screenerHeatRows(a,historicalMode?session:reported?.day,session,$('stkSessionQuality').value),historicalMode?session:reported?.day||session,$('stkSessionQuality').value==='all'):'<div class="sw-empty">No matching listings.</div>'):'';$('stockCount').textContent=`${a.length} of ${all.length} research listings`;
const pages=Math.max(1,Math.ceil(a.length/pageSize));currentPage=Math.min(currentPage,pages);$('stockPrev').disabled=currentPage<=1;$('stockNext').disabled=currentPage>=pages;$('stockPage').textContent='Page '+currentPage+' of '+pages;$('stocksRows').innerHTML=a.slice((currentPage-1)*pageSize,currentPage*pageSize).map(c=>`<tr><td><button type="button" class="sw-favorite" data-fav="${E(c.ticker)}" aria-label="Toggle ${E(c.name)} on watchlist">${favs.has(c.ticker)?'★':'☆'}</button><strong>${E(c.name)}</strong><small>${E(c.symbol||c.ticker)} · ${E(c.sector||'Other')}</small></td><td>${E(c.exchange||'—')}</td><td>${licensed.has(c.ticker)?`<strong>${N(licensed.get(c.ticker).close,4)} ${E(licensed.get(c.ticker).currency)}</strong><small>Licensed EOD · ${E(licensed.get(c.ticker).lastDate)}</small>`:c.pairQuote?`<strong>${N(c.pairQuote.close,4)} ${E(c.pairQuote.currency)}</strong><small>A/B observation · ${E(c.pairQuote.date)}</small>`:c.referenceOnly?'<small>Quote not connected</small>':c.unavailable?'<span class="sw-pill warn">Unavailable</span>':`${N(c.close,3)} <small>${E(c.currency||'')} · ${E(c.date||'Date unavailable')}${c.priceStatus==='retained'?' · last known':''}</small>`}</td><td>${chart(c.spark)}</td><td class="${c.marketQuality==='observed'?sign(c.changePct):'sw-neutral'}">${screen?.latestChange(c)!=null?P(c.changePct)+(c.marketQuality==='observed'?'':`<small>${E(c.date)} · reported</small>`):$('stkSessionQuality').value==='all'&&pairMapMove(c,historicalMode?session:reported?.day||session)?`${E(P(c.pairQuote.dailyMove.changePct))}<small>${E(c.pairQuote.dailyMove.date)} · A/B display only${c.pairQuote.retained||c.pairQuote.dailyMove.saved?' · saved':''}</small>`:$('stkSessionQuality').value==='all'&&savedScannerMove(c,historicalMode?session:reported?.day||session)?`${E(P(c.lastValidMovement.changePct))}<small>${E(c.lastValidMovement.date)} · saved movement</small>`:E(qualityLabel(c.marketQuality))}</td><td>${screen?.latestChange(c)!=null&&Number.isFinite(c.rvol)?N(c.rvol)+'×'+(c.marketQuality==='observed'?'':`<small>${E(c.date)} · reported</small>`):'—'}</td><td>${licensed.has(c.ticker)?`<a class="sw-row-action" href="${licensedHistoryUrl(c.ticker)}">Price history ↗</a>`:c.registryOnly?`<a class="sw-row-action" href="directory.html?q=${encodeURIComponent(c.figi)}">Identity ↗</a>`:c.referenceOnly?`<a class="sw-row-action" href="company.html?ticker=${encodeURIComponent('ref:'+c.referenceId)}">Research ↗</a>`:`<button type="button" class="sw-row-action" data-stock="${E(c.ticker)}">Details ↗</button>`}${displayChartLink(c)}</td></tr>`).join('')||'<tr><td colspan="7" class="sw-empty">No companies match these filters.</td></tr>';columns();$('stkTable').hidden=view!=='table';$('stkHeat').hidden=view!=='heat';document.querySelector('.sw-ws-pagination').hidden=view!=='table';}
const resetPage=()=>{currentPage=1;draw()};$('stockPrev').addEventListener('click',()=>{currentPage=Math.max(1,currentPage-1);draw()});$('stockNext').addEventListener('click',()=>{currentPage++;draw()});$('stkSearch').addEventListener('input',()=>{if($('stkSearch').value.trim()&&$('stkCoverage').value==='priced')$('stkCoverage').value='all';resetPage()});$('stkExchange').addEventListener('change',resetPage);$('stkCoverage').addEventListener('change',resetPage);$('stkSort').addEventListener('change',resetPage);$('stkCurrency').addEventListener('change',resetPage);$('stkSessionQuality').addEventListener('change',resetPage);document.querySelectorAll('[data-stk-view]').forEach(b=>b.addEventListener('click',()=>{view=b.dataset.stkView;document.querySelectorAll('[data-stk-view]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b))});resetPage();if(window.matchMedia('(max-width:760px)').matches)$('stkResults').scrollIntoView({block:'start',behavior:'instant'})}));$('stkColumns').addEventListener('change',e=>{const n=Number(e.target.dataset.stkColumn);if(!Number.isInteger(n))return;hiddenCols=e.target.checked?hiddenCols.filter(x=>x!==n):[...new Set([...hiddenCols,n])];try{localStorage.setItem('stockwatch-v51-columns',JSON.stringify(hiddenCols))}catch{}columns()});for(const id of ['stkMove','stkVolume','stkVolatility','stkSignal'])$(id).addEventListener('input',resetPage);const clearMetrics=()=>{for(const id of ['stkMove','stkVolume','stkVolatility'])$(id).value='';$('stkSignal').checked=false};$('stkResetMetrics').addEventListener('click',()=>{clearMetrics();resetPage()});document.querySelectorAll('[data-screen]').forEach(b=>b.addEventListener('click',()=>{clearMetrics();$('stkCoverage').value=b.dataset.screen==='all'?'all':'monitored';if(b.dataset.screen==='moves')$('stkMove').value='3';if(b.dataset.screen==='volume')$('stkVolume').value='2.5';if(b.dataset.screen==='signals')$('stkSignal').checked=true;document.querySelector('.sw-advanced-filters').open=b.dataset.screen!=='all';resetPage()}));document.querySelectorAll('[data-sector]').forEach(b=>b.addEventListener('click',()=>{currentPage=1;chosen=b.dataset.sector;document.querySelectorAll('[data-sector]').forEach(x=>x.classList.toggle('active',x===b));draw()}));$('favoriteOnly').addEventListener('click',()=>{currentPage=1;favoriteOnly=!favoriteOnly;$('favoriteOnly').classList.toggle('active',favoriteOnly);$('favoriteOnly').setAttribute('aria-pressed',String(favoriteOnly));draw()});$('stocksRows').addEventListener('click',e=>{const star=e.target.closest('[data-fav]');if(star){let t=star.dataset.fav;if(favs.has(t))favs.delete(t);else favs.add(t);try{localStorage.setItem('stockwatch-v4-favorites',JSON.stringify([...favs]))}catch{}draw();return}const b=e.target.closest('[data-stock]');if(b)openStock(b.dataset.stock)});if(registryMode)$('stkSort').value='name';if(!registryMode&&(historicalMode||params.get('coverage')==='monitored'))$('stkCoverage').value='monitored';else if(registryMode||params.get('q')||params.get('coverage')==='all')$('stkCoverage').value='all';else $('stkCoverage').value='priced';if(params.get('coverage')==='reference')$('stkCoverage').value='reference';if(historicalMode){$('stkSignal').disabled=true;document.querySelector('[data-screen="signals"]').disabled=true;}draw();const requested=params.get('ticker')==='PERR.PA'?'ALPER.PA':params.get('ticker');if(requested)openStock(requested)}
async function getHistory(t){if(state.history.has(t))return state.history.get(t);if(state.missingHistory.has(t))return null;try{const d=await get('data/history/'+encodeURIComponent(t)+'.json');if((d.publicDisplayPermitted!==true&&(d.publicDisplayPermitted!==undefined||d.redistributionPermitted!==true))||!d.licenseReference||!d.sourceUrl||!d.source||!d.currency||typeof d.adjusted!=='boolean'||!Array.isArray(d.bars)||!d.bars.length||d.ticker!==t)throw Error('unlicensed or empty');state.history.set(t,d);return d}catch{state.missingHistory.add(t);return null}}
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
function usSeedRows(data){
 return data?.schemaVersion===1&&Array.isArray(data.records)?data.records.filter(r=>r&&/^(XNAS|XNYS):[A-Z][A-Z0-9.-]{0,9}$/.test(r.id)&&r.id===r.mic+':'+r.symbol&&/^\d{10}$/.test(r.cik)&&r.identityStatus==='sec_ticker_exchange_association'&&r.quoteStatus==='not_connected'&&r.currency==='USD'&&r.sourceUrl==='https://www.sec.gov/files/company_tickers_exchange.json'):[];
}
function renderUSReference(root,ticker){
 const row=usSeedRows(state.usSeed).find(r=>r.id===ticker);if(!row)return false;
 document.title=row.name+' — US research reference | Stockwatch';
 const heading=document.querySelector('.sw-page-head h1');if(heading)heading.textContent=row.name;
 const rel=window.StockwatchRelationships,entity=rel?.entityForListing(state.relationships,row.id);
 root.innerHTML='<section class="sw-panel"><div class="sw-panel-pad"><div class="sw-company-banner"><div class="sw-company-heading"><div class="sw-ws-eyebrow">'+E(row.exchange)+' / '+E(row.symbol)+'</div><h2>'+E(row.name)+'</h2><p>'+E(row.group)+'</p></div><div class="sw-company-last"><small>Price status</small><strong>Not connected</strong><small>USD · reference only</small></div></div>'+(rel?.photo(state.companyPhotos,row.id)||'')+'<p class="sw-meta">SEC ticker/exchange association; price feed and licensed history not connected. No market signal is generated.</p><div class="sw-company-links"><a class="sw-soft-btn" href="https://www.sec.gov/edgar/browse/?CIK='+encodeURIComponent(row.cik)+'" target="_blank" rel="noopener noreferrer">SEC filings ↗</a><a class="sw-soft-btn" href="intelligence.html#usResearch">US research cohort ↗</a></div></div></section>'+(entity?'<div id="companyCommercialNetwork"></div>':'<p class="sw-meta">No reviewed commercial relationships for this issuer yet.</p>');
 const financial=document.createElement('section');financial.id='secCompanyFinancials';financial.className='sw-panel sw-panel-pad';financial.dataset.companySection='financials';root.firstElementChild.after(financial);
 window.StockwatchSECFinancials?.mount(financial,row,get);
 const jump=document.createElement('a');jump.className='sw-soft-btn';jump.href='#secCompanyFinancials';jump.textContent='Financial statements ↓';root.querySelector('.sw-company-links')?.prepend(jump);
 if(entity)rel.mount($('companyCommercialNetwork'),state.relationships,{selected:entity,review:state.relationshipReview,photos:null});
 const lens=window.StockwatchCompanyEvents,initial=lens?lens.select(state.archive?.items,{ticker:row.symbol,cik:row.cik}):[];
 const map=document.createElement('section');map.id='companyDriverMap';map.className='sw-panel';financial.after(map);
 const driverMap=window.StockwatchDriverMap?.mount(map,{company:{...row,ticker:row.id,driverKey:row.id},config:state.intelligence,load:get,events:initial,sections:root});
 if(lens){const section=document.createElement('section');section.className='sw-panel sw-panel-pad';section.id='companyEventLens';section.dataset.companySection='filings';root.append(section);lens.mount(section,initial,{sourceStatus:'Latest saved updates'});lens.load(get).then(items=>{if(section.isConnected){const records=lens.select(items,{ticker:row.symbol,cik:row.cik});lens.mount(section,records);driverMap?.updateEvents(records)}}).catch(()=>{});}
 return true;
}
function companyPage(){
 const requested=new URLSearchParams(location.search).get('ticker');
 const referenceId=String(requested||'').replace(/^ref:/,'');
 const target=(state.researchTargets?.targets||[]).find(x=>x.id===referenceId);
 const exact=target?companies().filter(x=>x.mic===target.mic&&x.isin===target.isin):[];
 const ticker=exact.length===1?exact[0].ticker:requested;
 const root=$('v4app'),c=companies().find(x=>x.ticker===ticker);
 if(!c&&renderUSReference(root,ticker))return;
 if(!c&&target){const evidence=(state.researchCoverage?.records||[]).find(x=>x.id===target.id&&x.mic===target.mic&&x.symbol===target.symbol&&x.isin===target.isin);
 const m=evidence?.currentCandidate||evidence?.lastCandidate||{},fields=[['Exchange MIC',target.mic],['Ticker',target.symbol],['Source-backed ISIN',target.isin],['FIGI candidate',m.figi],['Share-class FIGI candidate',m.shareClassFIGI],['Composite FIGI candidate',m.compositeFIGI],['Provider name',m.providerName],['Mapping method',m.method],['Last provider check',evidence?.lastChecked]];
 document.title=target.name+' — Company research | Stockwatch';const heading=document.querySelector('.sw-page-head h1');if(heading)heading.textContent=target.name;
 root.innerHTML='<section class="sw-panel sw-panel-pad"><div class="sw-company-banner"><div class="sw-company-heading"><div class="sw-ws-eyebrow">'+E(target.mic)+' / '+E(target.symbol)+'</div><h2>'+E(target.name)+'</h2><p>'+E(target.sector||'Reference research')+'</p></div></div><p class="sw-meta">Reference listing · no connected quote feed. FIGI candidates remain unverified.</p><div class="sw-identity-grid">'+fields.map(([k,v])=>'<div><small>'+E(k)+'</small><b>'+E(v||'Not available')+'</b></div>').join('')+'</div><div class="sw-company-links"><a class="sw-soft-btn" href="price-history.html?listing='+encodeURIComponent('ref:'+target.id)+'">Price research &amp; available chart ↗</a><a class="sw-soft-btn" href="intelligence.html?ticker='+encodeURIComponent('ref:'+target.id)+'">Connected intelligence ↗</a><a class="sw-soft-btn" href="research.html?instrument='+encodeURIComponent(target.id)+'#targetDetail">Original mapping history ↗</a></div><h3>Observed mapping history</h3><div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Observed UTC</th><th>Status</th><th>FIGI candidate</th></tr></thead><tbody>'+((evidence?.mappingHistory||[]).map(e=>'<tr><td>'+E(e.observedAt)+'</td><td>'+E(e.status)+'</td><td>'+E(e.mapping?.figi||'Unavailable')+'</td></tr>').join('')||'<tr><td colspan="3">No mapping observations recorded.</td></tr>')+'</tbody></table></div></section>';
 const map=document.createElement('section');map.id='companyDriverMap';map.className='sw-panel';root.firstElementChild.after(map);
 window.StockwatchDriverMap?.mount(map,{company:{...target,ticker:target.id,driverKey:target.id},config:state.intelligence,load:get,events:[],sections:root});return;
 }
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
 const research=window.StockwatchCompany,issuer=(state.issuers?.entities||[]).find(x=>x.ticker===t),events=state.events?.items||[],facts=state.fundamentals?.[t];
 const q=observationQuality(c,comparisonDate(state.signals?.generated));
 const attention=stockAttention([q==='observed'?c:{...c,changePct:null,rvol:null}],storyData())[0];
 container.dataset.currentTicker=t;
 container.innerHTML='<section class="sw-panel sw-company-research"><div class="sw-company-banner"><div class="sw-company-emblem" aria-hidden="true">'+E(c.name.split(/\s+/).slice(0,2).map(s=>s[0]).join('').toUpperCase().slice(0,3))+'</div><div class="sw-company-heading"><div class="sw-ws-eyebrow">'+E(c.exchange||'Trading venue unknown')+' / '+E(c.ticker)+'</div><h2>'+E(c.name)+'</h2><p>'+E(c.sector||'Unclassified')+'</p></div><div class="sw-company-last"><small>Latest observed close</small><strong>'+E(available?N(c.close,3)+' '+(c.currency||''):'Unavailable')+'</strong><b class="'+(q==='observed'?sign(c.changePct):'sw-neutral')+'">'+E(available&&Number.isFinite(c.changePct)&&c.volume>0?P(c.changePct)+(q==='observed'?'':' · reported '+(c.date||'')):qualityLabel(q))+'</b><small>'+E(c.date?'Price observation '+c.date+(c.priceStatus==='retained'?' · last known; latest refresh unavailable':''):'No price observation')+'</small></div></div>'+
 (research?research.coverageHTML({ticker:t,fundamental:facts,issuer,events,figis:(state.identities?.figiCandidates||[]).filter(x=>x.ticker===t).length,quality:qualityLabel(q),date:c.date}):'')+
 '<div class="sw-company-links"><a class="sw-soft-btn" href="stocks.html">Stocks directory</a>'+(page==='company'?'':'<a class="sw-primary" href="'+researchUrl+'">Open full research page ↗</a>')+'<a class="sw-soft-btn" href="https://finance.yahoo.com/quote/'+encodeURIComponent(c.ticker)+'" target="_blank" rel="noopener noreferrer">External price source ↗</a></div>'+
 '<div id="companyDriverMap"></div><div class="sw-company-tabs" aria-label="Research sections">'+[['chart','Price & activity'],['financials','Financials'],['filings','Company updates'],['peers','Peers'],['events','Corporate events'],['drivers','Industry drivers'],['identity','Identity']].map(([id,label])=>'<button type="button" data-company-tab="'+id+'" class="sw-soft-btn">'+label+'</button>').join('')+'</div>'+
 '<div class="sw-panel-pad"><div class="sw-company-block" data-company-section="chart"><div class="sw-stat-mini"><div><small>Relative volume</small><b>'+E(c.rvol==null?'—':N(c.rvol)+'×')+'</b></div><div><small>Vs watchlist market</small><b class="'+sign(c.excessPct)+'">'+P(c.excessPct)+'</b></div><div><small>Disclosed short</small><b>'+E(c.short?.percent==null?'—':N(c.short.percent)+'%')+'</b></div></div><div class="sw-section-row"><h2>Price history</h2><small>Source coverage determines available periods</small></div><div class="sw-controls">'+[[30,'1 month'],[90,'3 months'],[365,'1 year'],[1825,'5 years'],[0,'All available']].map(([d,l])=>'<button type="button" class="sw-soft-btn" data-period="'+d+'">'+l+'</button>').join('')+'</div><div class="sw-history-source" id="companyHistorySource">Checking history permissions…</div><div id="individualChart">Checking for dated history…</div><section id="companyEventLens" class="sw-company-block"></section><p class="sw-meta">Values are daily closes unless an adjusted series is verified. No simulated history or total-return calculation.</p><details class="sw50-external" open><summary>Optional external chart (separate provider)</summary>'+displayChartCard(c)+'</details></div>'+
 '<section class="sw-company-block" data-company-section="financials">'+(research?research.financialHTML(facts):renderFacts(c))+'</section>'+companyOperatingHTML(t)+investmentHTML(t)+roroMarketHTML(t)+freightScenarioHTML(t)+'<div id="freightAnalysis"></div>'+
 '<section class="sw-company-block" data-company-section="filings">'+(attention?attentionCard(attention):'')+'<div class="sw-section-row"><h2>Company updates</h2><a class="sw-textlink" href="news.html?q='+encodeURIComponent(c.ticker)+'">All source-linked news ↗</a></div>'+(updates.map(s=>storyBrief({...s,name:c.name,ticker:c.ticker})).join('')||'<p class="sw-meta">No recent source-linked company updates available.</p>')+'</section>'+
 '<section class="sw-company-block" data-company-section="peers"><div class="sw-section-row"><h2>Sector peers</h2><a class="sw-textlink" href="stocks.html?sector='+encodeURIComponent(c.sector||'')+'">Explore sector ↗</a></div><p class="sw-meta">Peers share the Stockwatch sector classification; this is not a verified ownership, competitive or supply-chain relationship. Price changes use the latest scanner observations.</p><div class="sw-company-peers">'+(peers.map(p=>'<a class="sw-peer" href="company.html?ticker='+encodeURIComponent(p.ticker)+'"><strong>'+E(p.name)+'</strong><small>'+E(p.ticker)+' · '+E(p.exchange||'')+'</small><span class="'+sign(p.changePct)+'">'+E(p.unavailable?'Unavailable':P(p.changePct))+'</span></a>').join('')||'<div class="sw-note">No other tracked listing in this sector.</div>')+'</div></section>'+
 '<section class="sw-company-block" data-company-section="events">'+(research?research.actionHTML(t,events,issuer):'<p class="sw-note">Corporate-event coverage unavailable.</p>')+'</section>'+
 '<section class="sw-company-block" data-company-section="identity">'+instrumentIdentityPanel(c.ticker)+'</section><section class="sw-company-block" data-company-section="drivers" id="companyDrivers"></section>'+intelligencePanel(c)+'</div></section>';
 const rel=window.StockwatchRelationships;
 if(rel){
  const banner=container.querySelector('.sw-company-banner'),photo=rel.photo(state.companyPhotos,t);
  if(banner&&photo)banner.insertAdjacentHTML('afterend',photo);
  const entity=rel.entityForListing(state.relationships,t);
  if(entity){const host=document.createElement('div');host.id='companyCommercialNetwork';container.append(host);rel.mount(host,state.relationships,{selected:entity,review:state.relationshipReview});}
 }
 const ownership=window.StockwatchOwnership;
 if(ownership&&t==='NHY.OL'){const host=document.createElement('section');host.className='sw-company-block';host.dataset.companySection='ownership-pilot';const drivers=container.querySelector('#companyDrivers');if(drivers)drivers.before(host);get('data/ownership-pilot-v1.json').then(d=>{if(host.isConnected&&container.dataset.currentTicker===t)ownership.mount(host,d,t)}).catch(()=>{});}
 mountFreightScenario(container);
 if(window.StockwatchIndustry)window.StockwatchIndustry.mount(container.querySelector('#companyDrivers'),{config:state.intelligence,sector:c.sector,ticker:t,load:get});
 container.querySelectorAll('[data-company-tab]').forEach(b=>b.addEventListener('click',()=>{const section=container.querySelector('[data-company-section="'+b.dataset.companyTab+'"]');if(section)section.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'})}));
 if(page!=='company')container.scrollIntoView({behavior:'smooth',block:'start'});
 const lens=window.StockwatchCompanyEvents,eventHost=container.querySelector('#companyEventLens');
 let chartController=null,companyEvents=lens?lens.select(state.archive?.items,{ticker:t}):[];
 const driverMap=window.StockwatchDriverMap?.mount(container.querySelector('#companyDriverMap'),{company:c,config:state.intelligence,load:get,events:companyEvents,sections:container});
 const eventOptions={sourceStatus:'Latest saved updates',onDate:d=>!!chartController?.inspectDate(d)};
 if(lens)lens.mount(eventHost,companyEvents,eventOptions);
 const archiveTask=lens?lens.load(get).then(items=>({events:lens.select(items,{ticker:t}),status:'Rolling archive'})).catch(()=>({events:companyEvents,status:'Latest saved updates · archive unavailable'})):Promise.resolve(null);
 let hist=await getHistory(t);
 const entry=(state.licensedPrices?.records||[]).find(p=>p.listingId===t&&(p.publicDisplayPermitted===true||(p.publicDisplayPermitted===undefined&&p.redistributionPermitted===true))&&p.priceType==='end_of_day'&&/^data\/licensed-reference-history\/[a-f0-9]{32}\.json$/.test(p.historyPath||''));
 if(entry&&window.StockwatchNativeChart){try{const payload=await get(entry.historyPath);if(window.StockwatchNativeChart.authorized(entry,payload))hist=payload}catch{}}
 if(container.dataset.currentTicker!==t)return;
 driverMap?.updateHistory(hist);
 const freightNode=container.querySelector('#freightAnalysis');if(freightNode)freightNode.innerHTML=freightAnalysisHTML(t,hist);
 const source=container.querySelector('#companyHistorySource');
 const allBars=hist?chartSeries(hist.bars.filter(x=>typeof x.close==='number'&&x.close>0).map(x=>({date:x.date,value:x.close}))):[];
 if(source)source.innerHTML=allBars.length?'<strong>Licensed historical close series</strong><span>'+E(hist.source)+' · '+E(hist.currency)+' · '+(hist.adjusted?'Adjusted closes (provider-defined)':'Unadjusted closes')+' · '+allBars.length+' observations</span><span>'+E(allBars[0].date)+' to '+E(allBars.at(-1).date)+'</span><a class="sw-textlink" href="'+E(link(hist.sourceUrl))+'" target="_blank" rel="noopener noreferrer">Source ↗</a> <a class="sw-textlink" href="'+E(link(hist.licenseReference))+'" target="_blank" rel="noopener noreferrer">Licence ↗</a>':'<strong>Licensed historical series not connected</strong><span>Latest scanner activity is separate from dated historical price data.</span><a class="sw-textlink" href="research.html">Historical coverage &amp; methodology ↗</a>';
 let selectedPeriod=365;
 const paint=days=>{selectedPeriod=days;chartController=null;const target=container.querySelector('#individualChart');if(!target)return;container.querySelectorAll('[data-period]').forEach(b=>{b.classList.toggle('active',+b.dataset.period===days);b.setAttribute('aria-pressed',String(+b.dataset.period===days))});if(allBars.length){if(window.StockwatchNativeChart){const cutoff=days?Date.parse(allBars.at(-1).date)-days*86400000:-Infinity;chartController=window.StockwatchNativeChart.mount(target,{label:c.name,unit:hist.currency,bars:hist.bars.filter(b=>Date.parse(b.date)>=cutoff),equity:true,events:companyEvents,source:hist.sourceUrl,notice:'Licensed dated observations · '+(hist.adjusted?'Adjusted':'Unadjusted')+' · '+hist.source})}else target.innerHTML=lineGraph(chartWindow(allBars,days),{label:c.name+' · daily close',unit:hist.currency});return}if(days===30&&c.spark?.length>1){target.innerHTML='<div class="sw-chart-empty"><strong>Undated recent scanner snapshot</strong><small>These closes lack individual date labels; this is not a dated price chart.</small><div class="sw-undated-spark">'+chart(c.spark,670,135)+'</div></div>';return}target.innerHTML=lineGraph([],{empty:'No licensed dated prices for this period.'})};
 container.querySelectorAll('[data-period]').forEach(b=>b.addEventListener('click',()=>paint(+b.dataset.period)));paint(365);
 archiveTask.then(result=>{if(!result||container.dataset.currentTicker!==t||!eventHost?.isConnected)return;companyEvents=result.events;driverMap?.updateEvents(companyEvents);lens.mount(eventHost,companyEvents,{...eventOptions,sourceStatus:result.status});if(allBars.length)paint(selectedPeriod)});
}
function onboardingPanel(){
 const rows=state.onboarding?.records||[];
 if(!rows.length)return '';
 return '<section class="sw-panel sw-onboarding">'+panelHeader('Research coverage expansion','Nordic directory','directory.html','Planned listings · no connected price feed')+'<div class="sw-panel-pad"><p class="sw-meta">'+rows.length+' additional Norwegian listings prioritized using exchange identity evidence. No change to the monitored universe until price access and identity mapping are established.</p><details><summary>View planned companies and ISINs</summary><div class="sw-onboard-grid">'+rows.map(x=>'<div><b>'+E(x.name)+'</b><small>'+E(x.ticker)+' · '+E(x.isin)+'</small></div>').join('')+'</div></details><p class="sw-meta"><a class="sw-textlink" href="'+E(link(state.onboarding.sourceUrl))+'" target="_blank" rel="noopener noreferrer">Original exchange reference ↗</a></p></div></section>';
}
function commodities(){const all=state.context?.commodities||[];let group='All';$('v4app').innerHTML=`<div class="sw-grid4">${stat('Metals',N(all.filter(x=>x.group==='metals').length,0),'Tracked market references')}${stat('Energy',N(all.filter(x=>x.group==='energy').length,0),'Tracked energy benchmarks')}${stat('Reported context',fmtDate(state.context?.generated),'Last saved data')}${stat('Source quality','Mixed','Direct quotes and labeled proxies')}</div><div class="sw-section-row"><h2>Market prices</h2><small>Latest known values · not live execution quotes</small></div><section class="sw-panel"><div class="sw-filter-row" id="commodityTabs"><button class="active" data-group="All">All markets</button><button data-group="metals">Metals</button><button data-group="energy">Energy</button></div><div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Commodity</th><th>Last</th><th>1 day</th><th>1 month</th><th>Year position</th><th>Source type</th></tr></thead><tbody id="commodityRows"></tbody></table></div></section>`;function draw(){let sub=group==='All'?all:all.filter(c=>c.group===group);$('commodityRows').innerHTML=sub.map(x=>`<tr><td><b>${E(x.name)}</b><small>${E(x.ticker||'')}</small></td><td>${N(x.last,3)}<small>${E(x.unit||'')} · ${E(x.date||'Observation date unavailable')}${x.observationStatus==='retained'?' · last known':''}</small></td><td class="${x.observationStatus==='retained'?'sw-neutral':sign(x.changePct)}">${P(x.changePct)}</td><td class="${sign(x.monthPct)}">${P(x.monthPct)}</td><td><div class="sw-valuebar"><i style="left:${Math.max(0,Math.min(97,Number(x.yearPosition||0)))}%"></i></div></td><td><span class="sw-pill ${x.proxy?'warn':''}">${x.proxy?'Proxy':'Market reference'}</span></td></tr>`).join('')};document.querySelectorAll('[data-group]').forEach(b=>b.addEventListener('click',()=>{group=b.dataset.group;document.querySelectorAll('[data-group]').forEach(x=>x.classList.toggle('active',x===b));draw()}));draw()}
function shorts(){const all=priced().filter(x=>x.short&&Number.isFinite(x.short.percent)).sort((a,b)=>b.short.percent-a.short.percent);$('v4app').innerHTML=`<div class="sw-grid4">${stat('Companies in register',N(all.length,0),'Tracked listings with records')}${stat('Highest disclosed',all.length?N(all[0].short.percent)+'%':'—',all[0]?.name||'No records')}${stat('Official register','Finanstilsynet','Norwegian disclosed holdings')}${stat('Not total interest','Thresholded','Small positions may be unreported')}</div><div class="sw-section-row"><h2>Disclosed short holdings</h2><a class="sw-textlink" target="_blank" rel="noopener noreferrer" href="https://ssr.finanstilsynet.no/">Official register ↗</a></div><section class="sw-panel"><div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Company</th><th>Current reported</th><th>Previous</th><th>Reporting funds</th><th>Largest holder</th><th>Register date</th></tr></thead><tbody>${all.map(x=>`<tr><td><b>${E(x.name)}</b><small>${E(x.ticker)}</small></td><td><b>${N(x.short.percent)}%</b></td><td>${N(x.short.previous)}%</td><td>${N(x.short.holders,0)}</td><td>${E(x.short.largest||'—')}<small>${x.short.largestPercent==null?'':N(x.short.largestPercent)+'%'}</small></td><td>${E(x.short.date||'')}</td></tr>`).join('')||'<tr><td colspan="6" class="sw-empty">No published short positions available.</td></tr>'}</tbody></table></div><div class="sw-note">Only publicly disclosed positions are listed. Older register entries may not represent current positions.</div></section>`}
// V63: sourced period-level issuer observations; never use as spot market rates.
function companyOperatingRows(data,ticker){
 const date=d=>typeof d==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d))&&new Date(d).toISOString().slice(0,10)===d;
 if(data?.schemaVersion!==1||!date(data.compiledOn)||!Array.isArray(data.companies))return [];
 const hosts={'WAWI.OL':'www.walleniuswilhelmsen.com','HAUTO.OL':'www.hoeghautoliners.com'};
 const counts=new Map();for(const c of data.companies)counts.set(c?.ticker,(counts.get(c?.ticker)||0)+1);
 return data.companies.filter(c=>c&&Object.hasOwn(hosts,c.ticker)&&counts.get(c.ticker)===1&&(!ticker||c.ticker===ticker)&&typeof c.issuer==='string'&&typeof c.scope==='string'&&Array.isArray(c.series)).map(c=>{
  const seen=new Set(),series=[];
  for(const v of c.series||[]){
   if(!v||typeof v.key!=='string'||seen.has(v.key)||typeof v.label!=='string'||typeof v.unit!=='string'||!['monthly','quarterly'].includes(v.frequency)||!Array.isArray(v.observations))continue;
   seen.add(v.key);
   const duplicates=new Map();
   for(const p of v.observations||[])duplicates.set(p?.periodEnd,(duplicates.get(p?.periodEnd)||0)+1);
   const observations=v.observations.filter(p=>{
    if(!p||duplicates.get(p.periodEnd)!==1||!date(p.periodEnd)||!date(p.publishedOn)||p.periodEnd>p.publishedOn||p.publishedOn>data.compiledOn||!Number.isFinite(p.value)||p.value<0)return false;
    if(v.unit==='%'&&p.value>100)return false;
    try{const u=new URL(p.sourceUrl);return u.protocol==='https:'&&!u.username&&!u.password&&typeof p.sourceLocator==='string'&&(u.hostname===hosts[c.ticker]||(c.ticker==='HAUTO.OL'&&u.hostname==='live.euronext.com'&&/^\/en\/products\/equities\/company-news\/\d{4}-\d{2}-\d{2}-hoegh-autoliners-asa-hauto-[a-z]+-\d{4}-trading-update$/.test(u.pathname)))}catch{return false}
   }).sort((a,b)=>a.periodEnd.localeCompare(b.periodEnd));
   if(observations.length)series.push({...v,observations});
  }
  return {...c,series};
 }).filter(c=>c.series.length);
}
// V66: match only recorded, authorized equity closes at consecutive reporting-period ends.
function freightPeriodAnalysis(series,history,ticker){
 const validDay=d=>typeof d==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d))&&new Date(Date.parse(d)).toISOString().slice(0,10)===d;
 const stride=series?.frequency==='monthly'?1:series?.frequency==='quarterly'?3:0;
 const monthIndex=d=>Number(d.slice(0,4))*12+Number(d.slice(5,7))-1;
 const monthEnd=d=>validDay(d)&&new Date(Date.parse(d)+86400000).getUTCDate()===1;
 const valid=!!(history&&history.ticker===ticker&&history.redistributionPermitted===true&&history.source&&history.sourceUrl&&history.licenseReference&&history.currency&&typeof history.adjusted==='boolean'&&Array.isArray(history.bars));
 const bars=new Map(),conflicts=new Set();
 if(valid)for(const b of history.bars){
  if(!b||!validDay(b.date)||!Number.isFinite(b.close)||b.close<=0)continue;
  if(bars.has(b.date)&&bars.get(b.date)!==b.close)conflicts.add(b.date);
  bars.set(b.date,b.close);
 }
 const dates=[...bars.keys()].filter(d=>!conflicts.has(d)).sort();
 const match=d=>{const v=dates.filter(x=>x<=d).at(-1);return v&&Date.parse(d)-Date.parse(v)<=7*86400000?{date:v,close:bars.get(v)}:null};
 const source=Array.isArray(series?.observations)?series.observations:[];
 const counts=new Map();for(const p of source)counts.set(p?.periodEnd,(counts.get(p?.periodEnd)||0)+1);
 const rows=stride?source.filter(p=>p&&monthEnd(p.periodEnd)&&validDay(p.publishedOn)&&p.publishedOn>=p.periodEnd&&counts.get(p.periodEnd)===1&&Number.isFinite(p.value)&&p.value>0&&(stride===1||Number(p.periodEnd.slice(5,7))%3===0)).sort((a,b)=>a.periodEnd.localeCompare(b.periodEnd)).map(p=>({...p,stock:match(p.periodEnd),rateChange:null,stockChange:null})): [];
 const pairs=[];
 for(let i=1;i<rows.length;i++){
  const a=rows[i-1],b=rows[i];
  if(monthIndex(b.periodEnd)-monthIndex(a.periodEnd)!==stride)continue;
  b.rateChange=100*(b.value/a.value-1);
  if(a.stock&&b.stock){b.stockChange=100*(b.stock.close/a.stock.close-1);pairs.push({period:b.periodEnd,x:b.rateChange,y:b.stockChange})}
 }
 // Descriptive correlation of consecutive changes, never of trending levels.
 let correlation=null;
 if(pairs.length>=12){
  const mx=pairs.reduce((n,p)=>n+p.x,0)/pairs.length,my=pairs.reduce((n,p)=>n+p.y,0)/pairs.length;
  const xx=pairs.reduce((n,p)=>n+(p.x-mx)**2,0),yy=pairs.reduce((n,p)=>n+(p.y-my)**2,0),xy=pairs.reduce((n,p)=>n+(p.x-mx)*(p.y-my),0);
  if(xx>1e-12&&yy>1e-12)correlation=Math.max(-1,Math.min(1,xy/Math.sqrt(xx*yy)));
 }
 return {rows,pairs,correlation,licensed:valid,minimum:12,currency:valid?history.currency:null,adjusted:valid?history.adjusted:null};
}
function freightAnalysisHTML(ticker,history){
 const links=reportedInvestments(state.investments).filter(r=>r.ownerTickers.includes(ticker)&&r.targetTicker);
 const direct=companyOperatingRows(state.companyOperating,ticker)[0],investee=links.map(r=>companyOperatingRows(state.companyOperating,r.targetTicker)[0]).find(Boolean);
 const issuer=direct||investee;if(!issuer)return '';
 const series=issuer.series.find(r=>r.key==='net_freight');if(!series)return '';
 const a=freightPeriodAnalysis(series,history,ticker),latest=a.rows.at(-1),quote=companies().find(r=>r.ticker===ticker);
 if(!latest)return '';
 return '<section class="sw-panel"><div class="sw-panel-hd"><div><h2>Stock versus reported freight</h2><small>'+E(ticker)+' · '+E(issuer.issuer)+' · '+E(series.frequency)+'</small></div></div><div class="sw-panel-pad"><p class="sw-meta">'+(direct?'Direct issuer operating economics.':'Indirect relationship through a disclosed investment; not the holding company’s own freight rate.')+' Period-end stock closes and freight results are aligned for retrospective comparison only. Results became public on their publication dates, not at period end.</p><div class="sw-stat-mini"><div><small>Latest share close</small><b>'+E(quote&&Number.isFinite(quote.close)?N(quote.close,3)+' '+quote.currency:'Unavailable')+'</b><small>'+E(quote?.date||'No observation')+'</small></div><div><small>Latest realized freight</small><b>'+E(N(latest.value,3)+' '+series.unit)+'</b><small>'+E(latest.periodEnd)+'</small></div><div><small>Consecutive freight change</small><b>'+E(latest.rateChange==null?'Not comparable':P(latest.rateChange))+'</b></div><div><small>Matched period changes</small><b>'+a.pairs.length+'</b><small>12 minimum for correlation</small></div></div><p class="sw-note">'+(a.licensed?(a.correlation==null?'Insufficient nonconstant, matched consecutive observations for correlation.':'Descriptive Pearson correlation: '+E(N(a.correlation,3))+' · '+a.pairs.length+' matched changes. Not a causal or predictive model.'):'Licensed dated share history not connected. Current scanner close is shown separately; undated spark data is never converted to historical prices.')+'</p><div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Period end</th><th>Freight ('+E(series.unit)+')</th><th>Freight change</th><th>Published</th><th>Period-end share close</th><th>Share change</th></tr></thead><tbody>'+a.rows.map(p=>'<tr><td>'+E(p.periodEnd)+'</td><td>'+E(N(p.value,3))+'</td><td>'+E(p.rateChange==null?'—':P(p.rateChange))+'</td><td><a href="'+E(p.sourceUrl)+'" target="_blank" rel="noopener noreferrer">'+E(p.publishedOn)+'</a></td><td>'+E(p.stock?N(p.stock.close,3)+' '+a.currency:'Not available')+(p.stock?'<small>'+E(p.stock.date)+'</small>':'')+'</td><td>'+E(p.stockChange==null?'—':P(p.stockChange))+'</td></tr>').join('')+'</tbody></table></div><small class="sw-meta">Only consecutive calendar months/quarters; last observed close no more than seven days before period end. '+(a.licensed?(a.adjusted?'Provider-adjusted':'Unadjusted')+' prices; no assumed dividend reinvestment. ':'')+'No interpolation, no invented dates, no look-ahead trading claims.</small></div></section>';
}
// V67: same-period realized freight x cargo volume, an illustrative revenue-scale
// sensitivity. Never equate this product with audited revenue, EBITDA or net income.
function freightScenario(rate,volume,ratePct,volumePct,costOffset){
 if(![rate,volume,ratePct,volumePct,costOffset].every(Number.isFinite)||rate<=0||volume<=0||ratePct< -100||ratePct>100||volumePct< -100||volumePct>100||Math.abs(costOffset)>1e6)return null;
 const baseline=rate*volume,changedRate=rate*(1+ratePct/100),changedVolume=volume*(1+volumePct/100),scenario=changedRate*changedVolume;
 const delta=scenario-baseline;
 return {baseline,changedRate,changedVolume,scenario,delta,costOffset,illustrativeContribution:delta-costOffset};
}
function freightScenarioBaseline(issuer){
 const rate=issuer?.series?.find(s=>s.key==='net_freight'&&s.unit==='USD/m³'),volume=issuer?.series?.find(s=>s.key==='transport_volume'&&s.unit==='million m³');
 if(!rate||!volume||rate.frequency!==volume.frequency)return null;
 const shared=rate.observations.filter(p=>volume.observations.some(v=>v.periodEnd===p.periodEnd&&v.publishedOn===p.publishedOn&&v.sourceUrl===p.sourceUrl)).sort((a,b)=>a.periodEnd.localeCompare(b.periodEnd)),r=shared.at(-1);
 if(!r)return null;
 const v=volume.observations.find(p=>p.periodEnd===r.periodEnd&&p.publishedOn===r.publishedOn&&p.sourceUrl===r.sourceUrl);
 if(!freightScenario(r.value,v.value,0,0,0))return null;
 return {rate:r.value,volume:v.value,periodEnd:r.periodEnd,publishedOn:r.publishedOn,sourceUrl:r.sourceUrl,frequency:rate.frequency};
}
function freightScenarioHTML(ticker){
 const direct=companyOperatingRows(state.companyOperating,ticker)[0],related=reportedInvestments(state.investments).filter(r=>r.ownerTickers.includes(ticker)&&r.targetTicker).map(r=>companyOperatingRows(state.companyOperating,r.targetTicker)[0]).find(Boolean),issuer=direct||related;
 const b=freightScenarioBaseline(issuer);if(!b)return '';
 return '<section class="sw-panel" id="freightScenario" data-freight-rate="'+b.rate+'" data-freight-volume="'+b.volume+'"><div class="sw-panel-hd"><div><h2>Freight &amp; cargo sensitivity</h2><small>'+E(issuer.issuer)+' · '+E(b.frequency)+' baseline</small></div></div><div class="sw-panel-pad"><p class="sw-meta">'+(direct?'Direct operating dataset.':'Investee operating scenario; not the holding company’s earnings or valuation.')+' Illustrative changes to net freight per cubic metre and cargo volume using the same disclosed reporting period. Rate × volume is a revenue-scale proxy, not audited revenue. Additional cost assumptions are user inputs, not company forecasts.</p><div class="sw-stat-mini"><div><small>Realized net freight</small><b>'+E(N(b.rate,3))+' USD/m³</b></div><div><small>Reported cargo volume</small><b>'+E(N(b.volume,3))+'m m³</b></div><div><small>Reporting period end</small><b>'+E(b.periodEnd)+'</b><small><a href="'+E(b.sourceUrl)+'" target="_blank" rel="noopener noreferrer">Published '+E(b.publishedOn)+' ↗</a></small></div></div><div class="sw-controls"><label>Freight rate change (%) <input id="freightRatePct" type="number" min="-100" max="100" step="1" value="0"></label><label>Cargo volume change (%) <input id="freightVolumePct" type="number" min="-100" max="100" step="1" value="0"></label><label>Additional costs (USD million) <input id="freightCostOffset" type="number" min="-1000000" max="1000000" step="1" value="0"></label><button class="sw-soft-btn" id="freightScenarioReset" type="button">Reset</button></div><div id="freightScenarioResults" aria-live="polite"></div><p class="sw-meta">Positive cost input subtracts from the illustrative change; negative cost input represents savings. Excludes taxes, contract mix, fleet deployment, pricing lag, hedges and other costs. No implied stock target, EBITDA or equity-accounted profit.</p></div></section>';
}
function mountFreightScenario(container){
 const root=container.querySelector('#freightScenario');if(!root)return;
 const inputs=['#freightRatePct','#freightVolumePct','#freightCostOffset'].map(id=>root.querySelector(id)),target=root.querySelector('#freightScenarioResults');
 const draw=()=>{const values=inputs.map(e=>e.value.trim()===''?NaN:Number(e.value)),r=freightScenario(Number(root.dataset.freightRate),Number(root.dataset.freightVolume),...values);
 if(!r){target.innerHTML='<p class="sw-note">Enter valid scenario assumptions within the displayed ranges.</p>';return}
 target.innerHTML='<div class="sw-stat-mini"><div><small>Baseline rate × volume proxy</small><b>USD '+E(N(r.baseline,2))+'m</b></div><div><small>Scenario rate × volume proxy</small><b>USD '+E(N(r.scenario,2))+'m</b></div><div><small>Change before extra costs</small><b class="'+sign(r.delta)+'">USD '+E(N(r.delta,2))+'m</b></div><div><small>Illustrative contribution change</small><b class="'+sign(r.illustrativeContribution)+'">USD '+E(N(r.illustrativeContribution,2))+'m</b></div></div>'};
 inputs.forEach(e=>e.addEventListener('input',draw));root.querySelector('#freightScenarioReset').addEventListener('click',()=>{inputs.forEach(e=>e.value='0');draw()});draw();
}
function companyOperatingHTML(ticker){
 const items=companyOperatingRows(state.companyOperating,ticker);
 if(!items.length)return '';
 return '<section class="sw-panel sw-company-operating" id="issuerOperatingMetrics"><div class="sw-panel-hd"><div><h2>Company-reported shipping economics</h2><small>Actual realized operating results, not spot route prices</small></div><a class="sw-textlink" href="'+(ticker?'shipping.html#issuerOperatingMetrics':'stocks.html?sector=Shipping%20%26%20offshore')+'">'+(ticker?'Freight intelligence ↗':'Shipping equities ↗')+'</a></div><div class="sw-panel-pad"><p class="sw-meta">Shipping-company reporting periods and cost definitions differ. Dates, units and original report links are preserved. No daily estimate or automatic freight-rate feed.</p>'+items.map(c=>{
 const rate=c.series.find(v=>v.key==='net_freight')||c.series[0],latest=rate.observations.at(-1);
 return '<article class="sw-card sw-panel-pad sw-operating-company"><div class="sw-section-row"><h3>'+E(c.issuer)+'</h3><a class="sw-textlink" href="company.html?ticker='+encodeURIComponent(c.ticker)+'">Company research ↗</a></div><p class="sw-meta">'+E(c.scope)+'</p><div class="sw-stat-mini">'+c.series.map(v=>{const p=v.observations.at(-1);return '<div><small>'+E(v.label)+'</small><b>'+E(N(p.value,3)+' '+v.unit)+'</b><small>'+E(p.periodEnd)+'</small></div>'}).join('')+'</div>'+lineGraph(rate.observations.map(p=>({date:p.periodEnd,value:p.value})),{label:rate.label+' · '+rate.frequency,unit:rate.unit})+'<p class="sw-meta">Latest period '+E(latest.periodEnd)+' · published '+E(latest.publishedOn)+' · <a class="sw-textlink" href="'+E(link(latest.sourceUrl))+'" target="_blank" rel="noopener noreferrer">Original disclosure ↗</a></p><details><summary>All reported observations and sources</summary><div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Metric</th><th>Period end</th><th>Value</th><th>Publication</th><th>Source</th></tr></thead><tbody>'+c.series.flatMap(v=>v.observations.map(p=>'<tr><td>'+E(v.label)+'</td><td>'+E(p.periodEnd)+'</td><td>'+E(N(p.value,3)+' '+v.unit)+'</td><td>'+E(p.publishedOn)+'</td><td><a class="sw-textlink" href="'+E(link(p.sourceUrl))+'" target="_blank" rel="noopener noreferrer">'+E(p.sourceLocator)+' ↗</a></td></tr>')).join('')+'</tbody></table></div></details></article>';
 }).join('')+'</div></section>';
}
// V65: port cargo volumes are not company-reported freight rates.
function roroTrafficRows(data){
 if(data?.schemaVersion!==1||data.provider!=='Eurostat'||data.datasetCode!=='mar_go_qmc'||!Array.isArray(data.series))return [];
 const allowed=new Set(['EU27_2020','NO','DE','BE','NL','DK','SE','FI','FR','ES']),seen=new Set(),result=[];
 const monthEnds=['03-31','06-30','09-30','12-31'];
 for(const row of data.series){
  if(!row||!allowed.has(row.countryCode)||seen.has(row.countryCode)||row.key!=='eurostat:mar_go_qmc:RO_TOT:'+row.countryCode||row.frequency!=='quarterly'||row.unit!=='thousand tonnes'||typeof row.label!=='string'||!Array.isArray(row.history))continue;
  const dates=new Set(),history=[];
  for(const p of row.history){
   if(!p||typeof p.period!=='string'||!/^\d{4}-Q[1-4]$/.test(p.period)||dates.has(p.period)||!Number.isFinite(p.value)||p.value<0)continue;
   dates.add(p.period);history.push({...p,date:p.period.slice(0,4)+'-'+monthEnds[Number(p.period.at(-1))-1]});
  }
  history.sort((a,b)=>a.period.localeCompare(b.period));if(!history.length)continue;
  seen.add(row.countryCode);result.push({...row,history,period:history.at(-1).period,value:history.at(-1).value});
 }
 return result;
}
function roroMarketHTML(ticker){
 if(ticker&&!['WWI.OL','WWIB.OL','WAWI.OL','HAUTO.OL'].includes(ticker))return '';
 const series=roroTrafficRows(state.roroTraffic);if(!series.length)return '';
 const eu=series.find(r=>r.countryCode==='EU27_2020'),no=series.find(r=>r.countryCode==='NO');
 const summary=[eu,no].filter(Boolean).map(r=>stat(r.label,N(r.value/1000,3)+'m tonnes',r.period+' · main ports')).join('');
 return '<section class="sw-panel" id="roroMarketTraffic"><div class="sw-panel-hd"><div><h2>European Ro-Ro cargo traffic</h2><small>Official Eurostat quarterly cargo weight</small></div><a class="sw-textlink" href="'+(ticker?'shipping.html#roroMarketTraffic':'https://ec.europa.eu/eurostat/databrowser/view/mar_go_qmc/default/table?lang=en')+'">'+(ticker?'All market data ↗':'Eurostat dataset ↗')+'</a></div><div class="sw-panel-pad"><p class="sw-meta">Broad sector context only: all Ro-Ro mobile units, not just passenger vehicles or this company’s cargo. No inference of issuer routes or market share. EU aggregate and countries overlap; do not sum.</p><div class="sw-grid4">'+summary+'</div>'+(ticker?'':'<div class="sw-controls"><label for="roroCountry">Reporting geography</label><select id="roroCountry">'+series.map(r=>'<option value="'+E(r.countryCode)+'">'+E(r.label)+'</option>').join('')+'</select></div><div id="roroTrafficChart"></div><details><summary>Latest available quarter by geography</summary><div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Geography</th><th>Quarter</th><th>Thousand tonnes</th><th>Flag</th></tr></thead><tbody>'+series.map(r=>'<tr><td>'+E(r.label)+'</td><td>'+E(r.period)+'</td><td>'+E(N(r.value,1))+'</td><td>'+E(r.history.at(-1).flag||'—')+'</td></tr>').join('')+'</tbody></table></div></details>')+'<p class="sw-meta">Source: <a href="https://ec.europa.eu/eurostat/databrowser/view/mar_go_qmc/default/table?lang=en" target="_blank" rel="noopener noreferrer">Eurostat mar_go_qmc</a> · <a href="https://ec.europa.eu/eurostat/help/copyright-notice" target="_blank" rel="noopener noreferrer">reuse terms</a> · Source snapshot accessed '+E(state.roroTraffic.observedOn||'Date unavailable')+'. Cards convert thousand tonnes to million tonnes. Missing quarters are not estimated.</p></div></section>';
}
function mountRoroMarket(){
 const control=$('roroCountry'),chartNode=$('roroTrafficChart');if(!control||!chartNode)return;
 const rows=roroTrafficRows(state.roroTraffic);
 const draw=()=>{const r=rows.find(x=>x.countryCode===control.value);if(r)chartNode.innerHTML=lineGraph(r.history.map(p=>({date:p.date,value:p.value})),{label:r.label+' · Ro-Ro cargo handled',unit:'thousand tonnes'})};
 control.addEventListener('change',draw);draw();
}
function shipping(){const all=state.routes;let category='Dry bulk',query='',routePage=1;const selected=new Set();const previews=state.context?.freight||[];$('v4app').innerHTML=`<div class="sw-hero"><div><div class="sw-kicker">GLOBAL FREIGHT INTELLIGENCE</div><strong>Track ship classes and trade routes separately.</strong><p>Capesize, Newcastlemax, Panamax, Supramax, tankers and container trade lanes. Route descriptions are sourced; daily benchmarks need redistribution rights.</p></div><a class="sw-primary" href="https://www.balticexchange.com/en/data-services/market-information0/indices.html" target="_blank" rel="noopener noreferrer">Benchmark definitions ↗</a></div><div class="sw-grid4">${stat('Tracked route definitions',N(all.length,0),'Published benchmark catalog')}${stat('Capesize / Newcastlemax','Separate classes','Newcastlemax is not a quote')}${stat('Benchmark rates',N(all.filter(x=>x.redistributionPermitted&&Number.isFinite(x.quote)).length,0)+' / '+N(all.length,0),'Licensed route observations')}${stat('Official shipping data','See below','Dated cost, throughput and connectivity indicators')}</div>${companyOperatingHTML()}${roroMarketHTML()}<div class="sw-section-row"><h2>Existing market proxies</h2><a class="sw-textlink" href="commodities.html">Related commodities ↗</a></div><div class="sw-tiles">${previews.map(x=>`<div class="sw-card sw-module" style="min-height:126px"><span class="sw-kicker">LISTED MARKET PROXY · NOT FREIGHT RATE</span><h3>${E(x.name)} · ${E(x.ticker||'')}</h3><p><strong>Security price ${N(x.last)} ${E(x.unit||'USD')}</strong> · <span class="${sign(x.changePct)}">${P(x.changePct)} reported</span></p><small class="sw-meta">${E(x.date||'Observation date unavailable')}${x.observationStatus==='retained'?' · last known':''}</small><small class="sw-meta">Not a direct shipping freight rate</small></div>`).join('')}</div><div id="shippingBenchmarkAnchor" class="sw-section-row"><h2>Routes & vessel classes</h2><small>Route units and source coverage</small></div><div class="sw-controls"><input id="routeSearch" placeholder="Search route, ship class, location…" type="search"><select id="routeVessel"><option value="all">All vessel classes</option></select></div><section class="sw-panel"><div id="shipCats" class="sw-filter-row"><button data-category="Dry bulk" class="active">Dry bulk</button><button data-category="Tankers">Tankers</button><button data-category="Containers">Containers</button></div><div class="sw-panel-pad"><div class="sw-route-list" id="routeGrid"></div><div id="routePager" class="sw-v48-pager" aria-label="Route pages"></div></div></section><section id="routeCompare" class="sw-panel sw-compare-route" aria-live="polite"><div class="sw-panel-hd"><div><h2>Compare trade routes</h2><small>Select up to four definitions. Quotes are compared only with matching units and licensed rates.</small></div></div><div id="routeCompareBody" class="sw-panel-pad"><div class="sw-note">Select Compare from the route cards.</div></div></section><div id="routeDetail"></div><div id="voyageEconomics"></div><div class="sw-tips">A freight route assessed in USD/tonne must not be presented as USD/day earnings. Public display and redistribution of Baltic Exchange benchmarks generally requires a suitable licence. Historical rate curves will only be enabled for sourced, permitted datasets.</div>`;
if(window.StockwatchVoyage)window.StockwatchVoyage.mount($('voyageEconomics'));
let types=[...new Set(all.map(x=>x.vessel))].sort();$('routeVessel').innerHTML+=[...types].map(x=>`<option value="${E(x)}">${E(x)}</option>`).join('');function draw(){const vessel=$('routeVessel').value,words=$('routeSearch').value.toLowerCase();let arr=all.filter(x=>x.category===category&&(vessel==='all'||x.vessel===vessel)&&`${x.code} ${x.name} ${x.vessel}`.toLowerCase().includes(words));const size=6,total=Math.max(1,Math.ceil(arr.length/size));routePage=Math.min(routePage,total);$('routePager').innerHTML=`<button class="sw-soft-btn" type="button" data-route-page="-1" ${routePage===1?'disabled':''}>Previous</button><span role="status">${arr.length?((routePage-1)*size+1)+'–'+Math.min(routePage*size,arr.length):'0'} of ${arr.length} routes</span><button class="sw-soft-btn" type="button" data-route-page="1" ${routePage===total?'disabled':''}>Next</button>`;$('routeGrid').innerHTML=arr.slice((routePage-1)*size,routePage*size).map(x=>`<article class="sw-card sw-route"><div class="sw-route-id">${E(x.code)}</div><h3>${E(x.name)}</h3><p>${E(x.vessel)} · ${E(x.unit)}</p><div class="sw-route-foot">${x.quote!=null&&x.redistributionPermitted?`<b>${N(x.quote,3)} ${E(x.unit)}</b>`:'<small>Benchmark quote unavailable</small>'}<button class="sw-row-action" type="button" data-compare="${E(x.code)}" aria-pressed="${selected.has(x.code)}">${selected.has(x.code)?'✓ Selected':'Compare'}</button><button class="sw-row-action" type="button" data-route="${E(x.code)}">Details ↗</button></div></article>`).join('')||'<div class="sw-empty">No routes found for these filters.</div>'}document.querySelectorAll('[data-category]').forEach(b=>b.addEventListener('click',()=>{category=b.dataset.category;routePage=1;document.querySelectorAll('[data-category]').forEach(x=>x.classList.toggle('active',x===b));draw()}));$('routeGrid').addEventListener('click',e=>{const c=e.target.closest('[data-compare]');if(c){const id=c.dataset.compare;if(selected.has(id))selected.delete(id);else if(selected.size<4)selected.add(id);draw();paintCompare();return}const b=e.target.closest('[data-route]');if(b)showRoute(b.dataset.route)});
function paintCompare(){const arr=[...selected].map(code=>all.find(x=>x.code===code)).filter(Boolean);const target=$('routeCompareBody');if(!arr.length){target.innerHTML='<div class="sw-note">Choose two to four routes to compare vessel class, units, and data coverage.</div>';return}const units=[...new Set(arr.map(x=>x.unit))];target.innerHTML=`<div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Route</th><th>Vessel class</th><th>Units</th><th>Rate</th><th>History</th></tr></thead><tbody>${arr.map(x=>`<tr><td><strong>${E(x.code)}</strong><small>${E(x.name)}</small></td><td>${E(x.vessel)}</td><td>${E(x.unit)}</td><td>${x.redistributionPermitted&&Number.isFinite(x.quote)?N(x.quote,2):'Licensed quote unavailable'}</td><td>${x.redistributionPermitted?'Check source history':'Pending rights'}</td></tr>`).join('')}</tbody></table></div><div class="sw-note">${units.length>1?'These routes use different pricing units and must not be plotted on one numerical axis.':'Same quote units; date-aligned comparison is enabled only when verified price series exist.'} No rates are estimated from shipping ETFs.</div>`;}
$('routePager').addEventListener('click',e=>{const b=e.target.closest('[data-route-page]');if(!b||b.disabled)return;routePage+=Number(b.dataset.routePage);draw();$('routePager').querySelector('[data-route-page="'+b.dataset.routePage+'"]:not([disabled])')?.focus()});const resetRoutes=()=>{routePage=1;draw()};$('routeSearch').addEventListener('input',resetRoutes);$('routeVessel').addEventListener('change',resetRoutes);draw();let routeSelection=0;async function showRoute(code){const request=++routeSelection;const r=all.find(x=>x.code===code);if(!r)return;const node=$('routeDetail');node.innerHTML=`<div class="sw-panel sw-detail">${panelHeader(r.name,'Official definition',link(r.sourceUrl),`${r.code} · ${r.vessel} · ${r.unit}`)}<div class="sw-panel-pad"><div class="sw-kicker">HISTORICAL ROUTE DATA</div><div id="routeChart" class="sw-chart-empty">Checking licensed historical series…</div><p class="sw-meta">A historical route series is shown only when the source explicitly permits redistribution. Data is labeled by date and unit.</p></div></div>`;node.scrollIntoView({behavior:'smooth',block:'start'});try{let h=await get('data/freight-history/'+encodeURIComponent(code)+'.json');if(h.redistributionPermitted!==true||h.unit!==r.unit||h.code!==r.code||!h.licenseReference||!Array.isArray(h.observations))throw Error('unlicensed');if(request!==routeSelection)return;let bars=h.observations.map(x=>({date:x.date,value:x.value}));$('routeChart').innerHTML=lineGraph(bars,{label:r.name+' freight history',unit:r.unit})}catch{if(request!==routeSelection)return;$('routeChart').innerHTML=lineGraph([],{empty:'Licensed route history not connected yet.'})}}}

async function renderUSDAOceanIndices(){
 const host=$('v4app');if(!host)return;
 const panel=document.createElement('section');panel.className='sw-panel';panel.id='usdaShippingIndices';
 panel.innerHTML='<div class="sw-panel-hd"><div><h2>USDA ocean grain freight cost indices</h2><small>Actual weekly historical data · 2017 = 100 · not USD/tonne freight quotes</small></div></div><div class="sw-panel-pad"><div class="sw-note" id="usdaShippingContent">Checking USDA historical index data…</div></div>';
 const routePanel=$('shippingBenchmarkAnchor');if(routePanel)routePanel.parentNode.insertBefore(panel,routePanel);else host.appendChild(panel);
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
 if(window.StockwatchNativeChart&&bars.length>=2)window.StockwatchNativeChart.mount(chart,{label:x.route,unit:x.unit,series:[{label:x.route,unit:x.unit,points:bars}],source:x.sourceUrl,notice:'Official USDA weekly cost index · 2017=100 · not a freight quote'});else chart.innerHTML=lineGraph(bars,{label:x.route+' · USDA index (2017=100)',unit:'index',empty:'At least two observations are required for a historical curve.'})
 };
 select.addEventListener('change',draw);draw();
}

async function renderFreightCostPPI(){
 const panel=document.createElement('section');panel.className='sw-panel';
 const anchor=$('shippingBenchmarkAnchor');if(anchor)anchor.parentNode.insertBefore(panel,anchor);else $('v4app').appendChild(panel);
 panel.innerHTML='<div class="sw-panel-hd"><div><h2>Deep-sea freight transportation prices</h2><small>US BLS producer price index · monthly · not a spot freight quote</small></div></div><div class="sw-panel-pad" id="freightPPIContent">Checking official observations…</div>';
 const host=$('freightPPIContent');let d;try{d=await get('data/economic-feeds.json')}catch{}
 const x=d?.series?.find(r=>r.key==='fred:PCU483111483111');
 if(!x||!Array.isArray(x.history)||!Number.isFinite(x.value)){host.innerHTML='<p class="sw-meta">Awaiting the first successful scheduled import. <a href="https://fred.stlouisfed.org/series/PCU483111483111" target="_blank" rel="noopener noreferrer">Official BLS series via FRED ↗</a></p>';return}
 host.innerHTML='<div class="sw-grid4">'+stat('Latest reported index',N(x.value,3),E(x.unit)) +stat('Observation period',E(x.period),'Monthly · not a daily rate')+'</div><div id="freightPPIChart"></div><p class="sw-meta">U.S. Bureau of Labor Statistics via <a href="https://fred.stlouisfed.org/series/PCU483111483111" target="_blank" rel="noopener noreferrer">FRED ↗</a> · public domain, citation requested. U.S. industry price index, not a quoted ocean route rate.</p>';
 const bars=x.history.filter(p=>Number.isFinite(p.value)&&/^\d{4}-\d{2}-\d{2}$/.test(p.date));const plot=$('freightPPIChart');
 if(window.StockwatchNativeChart&&bars.length>=2)window.StockwatchNativeChart.mount(plot,{label:x.label,unit:x.unit,series:[{label:x.label,unit:x.unit,points:bars}],source:x.sourceUrl,notice:'Monthly industry price index · not Baltic benchmark data'});else plot.innerHTML=lineGraph(bars,{label:x.label,unit:x.unit});
}
async function renderWorldBankPortTraffic(){
 const host=$('v4app');if(!host)return;
 const panel=document.createElement('section');panel.className='sw-panel';panel.id='worldBankPortTraffic';
 panel.innerHTML='<div class="sw-panel-hd"><div><h2>Global container-port activity</h2><small>World Bank / UNCTAD · annual container throughput (TEU) · not freight prices</small></div></div><div class="sw-panel-pad"><div class="sw-note" id="worldBankPortContent">Checking annual container-port activity…</div></div>';
 const routePanel=$('shippingBenchmarkAnchor');if(routePanel)routePanel.parentNode.insertBefore(panel,routePanel);else host.appendChild(panel);
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
 if(!['A-to-B','B-to-A'].includes(direction)||!p)return null;
 const from=direction==='A-to-B'?Number(p.aPrice):Number(p.bPrice);
 const to=direction==='A-to-B'?Number(p.bPrice):Number(p.aPrice);
 const amount=Number(holding),fee=Number(feePct)/100,slip=Number(slippagePct)/100,flat=Number(flatFee);
 if(![from,to,amount,fee,slip,flat].every(Number.isFinite)||from<=0||to<=0||!Number.isInteger(amount)||amount<1||amount>100000000||fee<0||fee>.10||slip<0||slip>.10||flat<0||flat>1000000)return null;
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
function pairReview(p,threshold,target,costs={holding:100,fee:.15,slippage:.2,flat:0}){
 const valid=x=>typeof x==='number'&&Number.isFinite(x);
 if(!p||![p.z,p.ratio,p.meanRatio,p.aPrice,p.bPrice,p.sd,p.days].every(valid)||p.ratio<=0||p.meanRatio<=0||p.aPrice<=0||p.bPrice<=0||p.sd<=0||p.days<60||!valid(threshold)||threshold<=0)return {status:'Insufficient data'};
 const direction=p.z>0?'A-to-B':p.z<0?'B-to-A':null;
 const fresh=!!target&&p.priceDate===target&&p.aLatestDate===target&&p.bLatestDate===target&&p.latestPairEligible===true&&!!p.currency;
 const passes=p.stationary===true&&p.tradableRange===true&&Math.abs(p.z)>=threshold;
 if(!direction)return {status:'At reference',fresh,passes:false};
 const q=switchEstimate(p,direction,costs.holding,costs.fee,costs.slippage,costs.flat);
 if(!q||q.shares<1)return {direction,fresh,passes,status:'Insufficient conversion size'};
 // Scenario only: B stays unchanged, ratio moves to the reference mean.
 const future={...p,aPrice:p.bPrice*p.meanRatio};
 const reverse=direction==='A-to-B'?'B-to-A':'A-to-B';
 const back=switchEstimate(future,reverse,q.shares,costs.fee,costs.slippage,costs.flat);
 const originalPrice=direction==='A-to-B'?future.aPrice:future.bPrice;
 const holding=Number(costs.holding);
 const equivalent=back?(back.shares+(q.remainder+back.remainder)/originalPrice):null;
 const net=equivalent===null?null:100*(equivalent/holding-1);
 const status=!fresh?'Price freshness unverified':!p.stationary?'Drift filter failed':!p.tradableRange?'Narrow historical range':!passes?'Below threshold':!valid(net)||net<=0?'Costs outweigh scenario': 'Threshold reached — review';
 return {status,direction,fresh,passes,net,shares:q.shares,trigger:fresh&&passes&&valid(net)&&net>0};
}
function pairDirectionLabel(d){return d==='A-to-B'?'Review switching A → B':d==='B-to-A'?'Review switching B → A':'No directional deviation'}
function spreadCurrency(t){if(/\.OL$/.test(t))return 'NOK';if(/\.ST$/.test(t))return 'SEK';if(/\.CO$/.test(t))return 'DKK';return 'listing currency'}
function switchingCalculator(pair){return `<div class="sw-panel sw-switch"><div class="sw-panel-hd"><div><h2>Share-class switching calculator</h2><small>Illustrative transaction costs · no execution recommendation</small></div></div>
<div class="sw-panel-pad"><div class="sw-calc-grid"><label>Direction<select id="abDirection"><option value="A-to-B">Sell A · buy B</option><option value="B-to-A">Sell B · buy A</option></select></label><label>Shares held<input id="abHoldings" type="number" min="1" max="100000000" step="1" value="100"></label><label>Broker fee per leg (%)<input id="abFee" type="number" min="0" max="10" step="0.05" value="0.15"></label><label>Slippage per leg (%)<input id="abSlippage" type="number" min="0" max="10" step="0.05" value="0.20"></label><label>Minimum fee per leg<input id="abFlat" type="number" min="0" max="1000000" step="1" value="0"></label></div><div id="abCalcResult" role="status" aria-live="polite"></div><p class="sw-meta">Uses last scanner closing prices, not tradable bid/ask quotes. Taxes, FX conversion, settlement, liquidity and differences in voting rights are excluded. B shares may not have the same voting rights as A shares.</p></div></div>`}
function bindSwitchingCalculator(root,pair){const ids=['abDirection','abHoldings','abFee','abSlippage','abFlat'];
 const paint=()=>{const q=switchEstimate(pair,$('abDirection').value,$('abHoldings').value,$('abFee').value,$('abSlippage').value,$('abFlat').value),el=$('abCalcResult');
 if(!q){el.innerHTML='<div class="sw-note">Enter positive prices and valid, non-negative costs.</div>';return}
 const side=$('abDirection').value==='A-to-B'?'B':'A',cur=pair.currency||spreadCurrency(pair.a),liq=window.StockwatchQuant?.liquidity(pair.aMedianVolume,pair.bMedianVolume,Number($('abHoldings').value));
 el.innerHTML=`<div class="sw-spread-facts"><div><small>Estimated ${side} shares received</small><b>${N(q.shares,0)}</b></div><div><small>Unspent cash (${E(cur)})</small><b>${N(q.remainder,2)}</b></div><div><small>Execution costs + slippage (${E(cur)})</small><b>${N(q.drag,2)}</b></div><div><small>Shares at 1Y mean (before costs)</small><b>${q.baseline===null?'—':N(q.baseline,2)}</b></div></div><p class="sw-meta">Estimated fees: sell ${N(q.sellFee,2)} / buy ${N(q.buyFee,2)} ${E(cur)}. Reference comparison describes history, not an expected future conversion ratio.</p>`+(liq?'<p class="sw-meta">Held share count as fraction of median volume: A '+N(liq.aPct,2)+'% / B '+N(liq.bPct,2)+'%. Not executable liquidity; ignores order-book depth and differences in shares received.</p>':'<p class="sw-meta">Median volume coverage insufficient for participation estimate.</p>');
 };ids.forEach(id=>$(id)?.addEventListener('input',paint));paint();}
function spreadSnapshotChart(pair,days=0){const key=pair.a+'/'+pair.b,raw=state.observations?.sessionPairs?.[key]||[],ok=raw.filter(x=>/^20\d\d-\d\d-\d\d$/.test(x.date)&&Number.isFinite(x.value)&&x.value>0).sort((a,b)=>a.date.localeCompare(b.date));
 const end=Date.parse(ok.at(-1)?.date),bars=days?ok.filter(x=>Date.parse(x.date)>=end-days*86400000):ok;
 if(bars.length<2)return '<div class="sw-chart-empty">Verified matched-session ratio snapshots are accumulating. Only '+bars.length+' dated observation(s) exist so far.<small>This is not a reconstructed 1Y price chart.</small></div>';
 // The public line starts from the first Stockwatch daily observation; it is
 // never retroactively synthesized from statistical summary data.
 return lineGraph(bars,{label:'Matched-session A/B ratio',unit:'A/B'})+`<p class="sw-meta">${bars.length} matched-session observations · earliest ${E(bars[0].date)} · original indicator snapshots, not licensed share-price bars. One observation per verified source session date; legacy scan-date snapshots excluded.</p>`;
}
function ratioReference(a){
 const mean=Number(a.meanRatio),sd=Number(a.sd),now=Number(a.ratio);
 if(![mean,sd,now].every(Number.isFinite)||sd<=0)return '<div class="sw-note">No numeric one-year reference summary is available.</div>';
 // The reference band uses existing scanner statistics. It is not a dated price history.
 const low=mean-3*sd,high=mean+3*sd,position=Math.max(0,Math.min(100,(now-low)/(high-low)*100));
 const premium=Number.isFinite(a.aPrice)&&Number.isFinite(a.bPrice)&&a.bPrice>0?(a.aPrice/a.bPrice-1)*100:NaN;
 return `<div class="sw-ref-card"><div class="sw-section-row"><h2>Last ratio against 1Y reference</h2><small>Statistical summary — NOT a price-history chart</small></div><div class="sw-ref-track" role="img" aria-label="Current A/B ratio ${N(now,4)}, 1-year mean ${N(mean,4)}, plus or minus two standard deviations"><div class="sw-ref-band"></div><div class="sw-ref-mean"></div><div class="sw-ref-marker" style="left:${position.toFixed(2)}%"></div></div><div class="sw-ref-labels"><span>−2σ: ${N(mean-2*sd,4)}</span><span>Mean: ${N(mean,4)}</span><span>+2σ: ${N(mean+2*sd,4)}</span></div><div class="sw-spread-facts"><div><small>${E(a.a||'A class')} last</small><b>${N(a.aPrice,3)}</b></div><div><small>${E(a.b||'B class')} last</small><b>${N(a.bPrice,3)}</b></div><div><small>A premium vs B</small><b>${Number.isFinite(premium)?P(premium):'—'}</b></div><div><small>Observed sessions</small><b>${N(a.days,0)}</b></div></div><p class="sw-meta">The green line marks the 1Y mean and the bright marker the latest ratio. The shaded area is ±2 standard deviations, not a trading range or a reconstructed time series. Economic rights, liquidity and fees can explain a persistent premium.</p></div>`;
}
function abDiscovery(){
 const rows=state.abCandidates?.records||[],checks=new Map((state.context?.shareClassCandidateChecks||[]).map(x=>[x.id,x]));
 const captions={source_unavailable:'Source unavailable',metadata_mismatch:'Provider identity not matched',currency_mismatch:'Currency mismatch',insufficient_aligned_observations:'Insufficient aligned prices',insufficient_volume:'Below volume threshold',price_checks_passed_identity_review_required:'Price checks passed · exact identity / rights review pending'};
 if(!rows.length)return '';
 return '<section class="sw-panel" id="abDiscovery">'+panelHeader('Additional A/B research candidates','Instrument directory','directory.html','Reference identities only · active listings and economic rights require review')+'<div class="sw-panel-pad"><div class="sw-intel-mini">'+rows.map(r=>'<div class="sw-peer"><small>'+E(r.venue)+'</small><strong>'+E(r.name)+'</strong><span><a class="sw-textlink" href="directory.html?q='+encodeURIComponent(r.a.figi)+'">A: '+E(r.a.ticker)+'</a> · <a class="sw-textlink" href="directory.html?q='+encodeURIComponent(r.b.figi)+'">B: '+E(r.b.ticker)+'</a></span><small>'+E(captions[checks.get(r.id)?.status]||'Collection check pending')+'</small><small>'+E(checks.get(r.id)?.alignedObservations!=null?checks.get(r.id).alignedObservations+' aligned observations':'')+'</small></div>').join('')+'</div><p class="sw-meta">OpenFIGI reference metadata identifies potential pairs; it does not establish equivalent dividend or voting rights, liquidity or active listing status. Candidate pairs are not included in tracked-pair statistics.</p></div></section>';
}
/* V30: descriptive, aligned-price analytics, no missing dates invented. */
function alignedPairStats(points){
 const a=chartSeries(points).filter(p=>p.value>0);const n=a.length;
 if(!n)return null;
 const mean=a.reduce((s,p)=>s+p.value,0)/n;
 const sd=n>1?Math.sqrt(a.reduce((s,p)=>s+(p.value-mean)**2,0)/(n-1)):null;
 const last=a.at(-1).value,low=a.reduce((v,p)=>Math.min(v,p.value),Infinity),high=a.reduce((v,p)=>Math.max(v,p.value),-Infinity);
 return {n,mean,sd,z:n>=30&&sd>0?(last-mean)/sd:null,last,low,high,premium:(last-1)*100,first:a[0].date,end:a.at(-1).date};
}
function alignedLicensedPair(ha,hb){
 if(!ha||!hb||ha.redistributionPermitted!==true||hb.redistributionPermitted!==true||!ha.currency||ha.currency!==hb.currency||typeof ha.adjusted!=='boolean'||ha.adjusted!==hb.adjusted||ha.source!==hb.source)return [];
 const clean=h=>chartSeries((h.bars||[]).filter(x=>typeof x.close==='number'&&x.close>0).map(x=>({date:x.date,value:x.close})));
 const b=new Map(clean(hb).map(x=>[x.date,x.value]));
 return clean(ha).filter(x=>b.has(x.date)).map(x=>({date:x.date,value:x.value/b.get(x.date)}));
}
function thresholdEpisodes(points,lookback=60,limit=2){
 if(!Number.isInteger(lookback)||lookback<30||!Number.isFinite(limit)||limit<=0||!Array.isArray(points))return null;
 const p=points.filter(x=>x&&Number.isFinite(x.value)&&x.value>0&&/^\d{4}-\d{2}-\d{2}$/.test(x.date)).slice().sort((a,b)=>a.date.localeCompare(b.date));
 if(p.length<=lookback||new Set(p.map(x=>x.date)).size!==p.length)return null;
 let active=null,completed=[],entries=0;
 for(let i=lookback;i<p.length;i++){
  const v=p[i].value;
  if(active){if(active.side*(v-active.mean)<=0){completed.push(i-active.index);active=null}continue}
  const prior=p.slice(i-lookback,i).map(x=>x.value),mean=prior.reduce((a,b)=>a+b,0)/lookback;
  const sd=Math.sqrt(prior.reduce((a,b)=>a+(b-mean)**2,0)/lookback);
  if(sd>0){const z=(v-mean)/sd;if(Math.abs(z)>=limit){active={index:i,mean,side:Math.sign(z)};entries++}}
 }
 completed.sort((a,b)=>a-b);const m=Math.floor(completed.length/2);
 return {entries,completed:completed.length,unresolved:active?1:0,medianSessions:completed.length?(completed.length%2?completed[m]:(completed[m-1]+completed[m])/2):null};
}
function thresholdEpisodePanel(points){
 const x=thresholdEpisodes(points);
 if(!x)return '<p class="sw-meta">Threshold history needs more than 60 aligned licensed observations.</p>';
 return '<div class="sw-spread-stats"><div><small>2σ episodes</small><b>'+N(x.entries,0)+'</b></div><div><small>Reached entry reference</small><b>'+N(x.completed,0)+'</b></div><div><small>Unresolved at end</small><b>'+N(x.unresolved,0)+'</b></div><div><small>Median completed sessions</small><b>'+N(x.medianSessions,1)+'</b></div></div><p class="sw-meta">Walk-forward: 60 preceding observations determine the entry mean and deviation; exit checks the fixed entry mean, one episode at a time. Unresolved episodes are not counted as completed. Descriptive, excludes execution, costs and taxes; not a strategy success rate or forecast.</p>';
}
function robustPairPanel(points){const q=window.StockwatchQuant?.summary(points);if(!q)return '';return '<div class="sw-spread-stats"><div><small>Sample observations</small><b>'+N(q.n,0)+'</b></div><div><small>Median ratio</small><b>'+N(q.median,4)+'</b></div><div><small>10th – 90th percentile</small><b>'+N(q.p10,4)+' / '+N(q.p90,4)+'</b></div><div><small>Median absolute deviation z-score</small><b>'+N(q.robustZ,2)+'</b></div></div><p class="sw-meta">Robust statistics require 30 matched observations and nonzero median absolute deviation for the robust z-score. Descriptive only.</p>'}
function pairStatsPanel(points){
 const s=alignedPairStats(points);if(!s)return '';
 const m=(k,v)=>'<div><small>'+E(k)+'</small><b>'+E(v)+'</b></div>';
 return '<div class="sw-spread-stats">'+m('Aligned observations',s.n)+m('Window mean',N(s.mean,4))+m('Latest premium',N(s.premium,2)+'%')+m('Window z-score',s.z===null?'Insufficient variation / sample':N(s.z,2)+'σ')+'</div><p class="sw-meta">Descriptive sample statistics for '+E(s.first)+' — '+E(s.end)+'. Z-score requires at least 30 aligned observations; not a stationarity test or trading signal.</p>';
}
async function spreads(){const all=state.context?.shareClasses||[];if(!all.length){$('v4app').innerHTML='<div class="sw-note">Share-class data is unavailable in the latest market context.</div>'+abDiscovery();return}let chosen=all.find(x=>x.stationary&&x.tradableRange)||all[0];const target=comparisonDate(state.context?.generated),freshCount=all.filter(p=>p.priceDate===target&&p.aLatestDate===target&&p.bLatestDate===target&&p.latestPairEligible===true).length,feed=state.context?.shareClassFeedHealth||[];$('v4app').innerHTML=`<div class="sw-grid4">${stat('Tracked A/B pairs',N(all.length,0),'Derived from listed share classes')}${stat('Low-drift candidates',N(all.filter(x=>x.stationary).length,0),'Split-half drift heuristic, not a formal test')}${stat('Additional research pairs',N(state.abCandidates?.records?.length||0,0),'Reference candidates, no prices')}${stat('Ratio observations','Daily snapshots','Backfill only from licensed price series')}</div><section class="sw-panel"><div class="sw-panel-pad"><h2>Price feed reliability</h2><p class="sw-meta">${freshCount} / ${all.length} tracked pairs have eligible matched prices for comparison date ${E(target||"unknown")}. No current threshold alert for older or invalid bars.</p><details><summary>Provider diagnostics (${feed.length} pairs)</summary><div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Pair</th><th>A latest bar</th><th>B latest bar</th></tr></thead><tbody>${feed.map(x=>`<tr><td>${E(x.name)}</td><td>${E(x.aHealth.status)} · ${E(x.aHealth.reportedDate||"—")}</td><td>${E(x.bHealth.status)} · ${E(x.bHealth.reportedDate||"—")}</td></tr>`).join("")}</tbody></table></div></details></div></section><div class="sw-section-row"><h2>Share class pairs</h2><small>Select a company for deeper analysis</small></div><div class="sw-pairs" id="spreadPairs"></div><section class="sw-panel sw-ab-ranking"><div class="sw-panel-pad"><h2>Spread watchlist</h2><p class="sw-meta">Ranked by absolute historical deviation; direction is relative to the mean, not a trading instruction. Default scenario: 100 shares, 0.15% fee and 0.20% slippage per leg, 2σ threshold.</p><div class="sw-tablewrap"><table class="sw-table"><thead><tr><th>Pair</th><th>Deviation</th><th>Relative-value review</th><th>Hypothetical net return</th><th>Data status</th></tr></thead><tbody>${all.slice().sort((a,b)=>Math.abs(b.z)-Math.abs(a.z)).map(p=>{const q=pairReview(p,2,target);return `<tr><td><button type="button" data-review-pair="${all.indexOf(p)}" class="sw-soft-btn">${E(p.name)}</button></td><td>${N(p.z,2)}σ</td><td>${E(pairDirectionLabel(q.direction))}</td><td>${Number.isFinite(q.net)?P(q.net):"—"}</td><td>${E(q.status)}</td></tr>`}).join("")}</tbody></table></div></div></section><section class="sw-panel" id="spreadDetail"></section><div class="sw-tips">Historical deviations are descriptive, not automatic buy/sell signals. Compare the same-day prices in the same currency, confirm identical economic rights, trading costs, liquidity, corporate actions and that a spread is statistically stable. A drifting pair should not be described as mean-reverting.</div>${abDiscovery()}`;const host=$('spreadPairs');document.querySelectorAll('[data-review-pair]').forEach(b=>b.addEventListener('click',()=>host.querySelector('[data-pair="'+b.dataset.reviewPair+'"]').click()));host.innerHTML=all.map((x,i)=>`<button data-pair="${i}" class="${x===chosen?'active':''}">${E(x.name)}</button>`).join('');host.addEventListener('click',e=>{let b=e.target.closest('[data-pair]');if(b){chosen=all[+b.dataset.pair];host.querySelectorAll('button').forEach(x=>x.classList.toggle('active',x===b));show()}});
async function show(){const a=chosen;const root=$('spreadDetail');root.innerHTML=`${panelHeader(`${a.name} · share-class ratio`,'Company comparisons','compare.html',`${a.a||'A class'} / ${a.b||'B class'}`)}<div class="sw-panel-pad"><div class="sw-spread-stats"><div><small>Last observed A/B ratio</small><b>${N(a.ratio,4)}</b></div><div><small>Difference vs 1Y mean</small><b>${a.stationary?N(a.z,2)+'σ':'Drifting'}</b></div><div><small>Observed range</small><b>${N(a.rangePct)}%</b></div><div><small>Time-series status</small><b>${a.stationary?'Stable by drift heuristic':'Not stationary'}</b></div></div>${ratioReference(a)}<div class="sw-panel sw-panel-pad"><div class="sw-section-row"><h2>Rolling ratio references</h2><small>Trading observations, not calendar days</small></div><div class="sw-spread-facts">${[30,90,240].map(n=>{const x=a.rolling?.[String(n)];return `<div><small>${n} observations</small><b>${x?N(x.mean,4):'—'}</b><small>${Number.isFinite(x?.z)?N(x.z,2)+'σ':'Insufficient validated data'}</small></div>`}).join('')}<div><small>Median daily share volume A / B</small><b>${N(a.aMedianVolume,0)} / ${N(a.bMedianVolume,0)}</b></div></div></div>${switchingCalculator(a)}<div class="sw-panel sw-alerts"><div class="sw-panel-pad"><h2>In-page A/B threshold monitor</h2><div class="sw-controls"><label><input id="abFollow" type="checkbox"> Watch this pair</label><label>Z-score threshold <select id="abThreshold"><option value="1">1.0σ</option><option value="1.5">1.5σ</option><option value="2">2.0σ</option><option value="2.5">2.5σ</option></select></label></div><div id="abAlertText" class="sw-note" role="status"></div><small class="sw-meta">Browser-local threshold review only, not push or email. Requires matched fresh prices and a positive hypothetical net result after four transaction legs. Voting/dividend rights, tax, liquidity and corporate actions require independent review. No mean-reversion guarantee.</small></div></div><div class="sw-section-row"><h2>Historical price ratio</h2><small>Same-day A ÷ B closes · licensed data only</small></div><div class="sw-chart-tools"><button type="button" data-spread-window="30">1M</button><button type="button" data-spread-window="90">3M</button><button type="button" data-spread-window="365" class="active">1Y</button><button type="button" data-spread-window="0">All</button></div><div id="spreadGraph" class="sw-chart-empty">Checking aligned, dated A/B prices…</div><div class="sw-metric-inline"><span>One-year reference ratio</span><b>${N(a.meanRatio,4)}</b></div><div class="sw-metric-inline"><span>Reported variation (standard deviation)</span><b>${N(a.sd,4)}</b></div><p class="sw-meta">Pair ${E(a.a||'A class')} vs ${E(a.b||'B class')}. The chart is only drawn when real source histories are available for both listings. It is not an execution signal.</p></div>`;
bindSwitchingCalculator(root,a);
const storeKey='stockwatch-final-pair-watches';let saved={};try{saved=JSON.parse(localStorage.getItem(storeKey)||'{}')||{}}catch{}
const watchId=a.a+'/'+a.b;
$('abFollow').checked=!!saved[watchId];$('abThreshold').value=String(saved[watchId]?.threshold||2);
const alertPaint=()=>{const limit=Number($('abThreshold').value),q=pairReview(a,limit,target,{holding:$('abHoldings').value,fee:$('abFee').value,slippage:$('abSlippage').value,flat:$('abFlat').value});
 $('abAlertText').textContent=pairDirectionLabel(q.direction)+' · '+q.status+' · '+(a.priceDate?'Matched price date '+a.priceDate:'Matched price date unavailable')+(Number.isFinite(q.net)?' · Hypothetical net round-trip '+P(q.net)+' if ratio returns to mean (B price fixed; includes fees and slippage, excludes tax)':'');
 $('abAlertText').classList.toggle('sw-alert-active',!!q.trigger&&$('abFollow').checked);
 try{if($('abFollow').checked)saved[watchId]={threshold:limit};else delete saved[watchId];localStorage.setItem(storeKey,JSON.stringify(saved))}catch{}
};$('abFollow').addEventListener('change',alertPaint);$('abThreshold').addEventListener('change',alertPaint);['abHoldings','abFee','abSlippage','abFlat'].forEach(id=>$(id).addEventListener('input',alertPaint));alertPaint();
const [ha,hb]=await Promise.all([getHistory(a.a),getHistory(a.b)]);if(chosen!==a)return;const graph=$('spreadGraph');if(!ha||!hb||ha.redistributionPermitted!==true||hb.redistributionPermitted!==true||!ha.currency||ha.currency!==hb.currency||ha.adjusted!==hb.adjusted){const paintObs=(days=365)=>{root.querySelectorAll('[data-spread-window]').forEach(b=>b.classList.toggle('active',Number(b.dataset.spreadWindow)===days));graph.innerHTML=spreadSnapshotChart(a,days)+robustPairPanel((state.observations?.sessionPairs?.[watchId]||[]).filter(x=>!days||Date.parse(x.date)>=Math.max(...(state.observations?.sessionPairs?.[watchId]||[]).map(r=>Date.parse(r.date)))-days*86400000))+`<p class="sw-meta">Licensed daily share-price histories are unavailable for this pair; showing only separately recorded matched-session indicator snapshots when available.</p>`};root.querySelectorAll('[data-spread-window]').forEach(b=>b.addEventListener('click',()=>paintObs(Number(b.dataset.spreadWindow))));paintObs();return}const points=alignedLicensedPair(ha,hb);const paint=(windowDays=365)=>{root.querySelectorAll('[data-spread-window]').forEach(b=>b.classList.toggle('active',Number(b.dataset.spreadWindow)===windowDays));const latest=Date.parse(points.at(-1)?.date);const display=windowDays?points.filter(p=>Date.parse(p.date)>=latest-windowDays*86400000):points;graph.innerHTML=lineGraph(display,{label:'Historical A to B price ratio',unit:'A/B',empty:'Not enough licensed price observations in this date range.'})+pairStatsPanel(display)+robustPairPanel(display)+thresholdEpisodePanel(display)+`<p class="sw-meta">${N(display.length,0)} aligned observations · ${E(ha.source||'Price source')} / ${E(hb.source||'Price source')} · ${E(ha.currency)}. Split/dividend adjustments and share-class rights must be verified.</p>`};root.querySelectorAll('[data-spread-window]').forEach(b=>b.addEventListener('click',()=>paint(Number(b.dataset.spreadWindow))));paint()}
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
function nav(){const workspace=document.querySelector('.sw-nav-group:first-child .sw-links');if(workspace&&!workspace.querySelector('a[href="terminal.html"]')){const t=document.createElement('a');t.href='terminal.html';t.className='sw-link'+(page==='terminal'?' active':'');if(page==='terminal')t.setAttribute('aria-current','page');t.innerHTML='<span class="sw-link-icon">▦</span><span>Research terminal</span><span class="sw-link-arr">›</span>';workspace.insertBefore(t,workspace.children[1]||null)}const group=document.querySelector('.sw-nav-group:last-child .sw-links');if(group){for(const [href,label,icon] of [['welcome.html','About Stockwatch','◫'],['directory.html','Instrument directory','▥'],['research.html','Research methodology','◉'],['intelligence.html','Intelligence graph','◇']]){if(document.querySelector('.sw-side a[href="'+href+'"]'))continue;const a=document.createElement('a');a.className='sw-link';a.href=href;const i=document.createElement('span');i.className='sw-link-icon';i.textContent=icon;const t=document.createElement('span');t.textContent=label;a.append(i,t);group.appendChild(a)}}const mark=document.querySelector('.sw-logo-mark');if(mark){const img=document.createElement('img');img.src='brand/stockwatch.svg';img.alt='';img.width=36;img.height=36;mark.replaceChildren(img)}const favicon=document.querySelector('link[rel="icon"]');if(favicon)favicon.href='brand/stockwatch.svg';let theme;try{theme=localStorage.getItem('stockwatch-theme')}catch{}theme=theme==='light'?'light':'dark';document.body.dataset.theme=theme;$('swTheme').textContent=theme==='light'?'☀':'☾';$('swTheme').onclick=()=>{let now=document.body.dataset.theme==='light'?'dark':'light';document.body.dataset.theme=now;$('swTheme').textContent=now==='light'?'☀':'☾';try{localStorage.setItem('stockwatch-theme',now)}catch{}};$('swSearchForm').addEventListener('submit',e=>{e.preventDefault();let q=$('swGlobalSearch').value.trim();location.href='stocks.html'+(q?'?q='+encodeURIComponent(q):'')});document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('swGlobalSearch').focus()}})}
async function init(){nav();wireChartInspector();wireDisplayCharts();const files=[['signals','data/signals.json'],['context','data/context.json'],['watchlist','watchlist.json'],['routes','data/freight-routes.json'],['archive','data/news-latest.json'],['health','data/source-health.json'],['fundamentals','data/fundamentals.json'],['observations','data/spread-observations.json'],['identities','data/registered-source-status.json'],['issuers','data/issuer-identities.json'],['onboarding','data/research-onboarding.json'],['researchTargets','data/research-targets.json'],['researchCoverage','data/research-coverage.json'],['intelligence','data/intelligence-context.json'],['expansion','data/research-expansion.json'],['licensedPrices','data/licensed-price-coverage.json'],...(['stocks','company','shipping','intelligence'].includes(page)?[['companyOperating','data/company-operating-metrics.json'],['investments','data/issuer-investments.json'],['roroTraffic','data/shipping-roro-traffic.json']]:[]),...(['stocks','company','intelligence'].includes(page)?[['relationships','data/company-relationships.json'],['relationshipReview','data/relationship-review.json'],['companyPhotos','data/company-image-catalog.json'],['usSeed','data/us-equity-seed.json']]:[]),...(['stocks','company'].includes(page)?[['events','data/events.json']]:[]),...(['stocks','company','licensedPrices'].includes(page)?[['chartDisplays','data/chart-display-symbols.json']]:[]),...(page==='spreads'?[['abCandidates','data/ab-research-candidates.json']]:[]),...(['index','stocks'].includes(page)?[['referenceDirectory','data/instrument-directory.json']]:[])];const required=page==='index'?files.filter(([k])=>['signals','context','watchlist','archive','health','researchTargets','researchCoverage','expansion'].includes(k)):files;const data=await Promise.all(required.map(async([k,p])=>{try{return [k,await get(p)]}catch{return [k,null]}}));const o=Object.fromEntries(data);state.signals=o.signals;state.context=o.context;state.watchlist=o.watchlist?.tickers||[];state.routes=o.routes?.routes||[];state.archive=o.archive;state.health=o.health;state.fundamentals=o.fundamentals?.companies||{};state.observations=o.observations;state.identities=o.identities;state.issuers=o.issuers;state.onboarding=o.onboarding;state.researchTargets=o.researchTargets;state.researchCoverage=o.researchCoverage;state.intelligence=o.intelligence;state.referenceDirectory=o.referenceDirectory;state.expansion=o.expansion;state.licensedPrices=o.licensedPrices;state.abCandidates=o.abCandidates;state.chartDisplays=o.chartDisplays;state.events=o.events;state.companyOperating=o.companyOperating;state.investments=o.investments;state.roroTraffic=o.roroTraffic;state.relationships=o.relationships;state.relationshipReview=o.relationshipReview;state.companyPhotos=o.companyPhotos;state.usSeed=o.usSeed;wireQuickSearch();const label=$('swRefreshLabel');if(state.signals?.generated)label.textContent='Scan '+timeAge(state.signals.generated);else label.textContent='Data unavailable';if(state.signals?.generated)$('swSourceStatus').textContent='Last scan '+fmtDate(state.signals.generated);tape();if(page==='terminal'){await window.StockwatchTerminal.render({root:$('v4app'),companies:companies(),universe:directoryRows(),signals:state.signals,context:state.context,licensedPrices:state.licensedPrices});await window.StockwatchResearchLab.mount({root:$('v4app'),companies:companies(),universe:directoryRows(),signals:state.signals,context:state.context,licensedPrices:state.licensedPrices,fundamentals:state.fundamentals,intelligence:state.intelligence});return}if(page==='health'){renderMarketCoverage();return}if(['news','calendar','compare'].includes(page))return;if((!state.watchlist.length&&!(['stocks','intelligence'].includes(page)&&state.researchTargets?.targets?.length))||(!state.signals&&!['index','stocks','company','intelligence','licensedPrices'].includes(page))){$('v4app').innerHTML='<div class="sw-note sw-notice">The scanner dataset is unavailable. The interface does not invent market data.</div>';return}if(page==='index')overview();else if(page==='stocks')stocks();else if(page==='licensedPrices')await licensedPricePage();else if(page==='company')await companyPage();else if(page==='intelligence')await intelligencePage();else if(page==='spreads')await spreads();else if(page==='shipping'){shipping();mountRoroMarket();await renderUSDAOceanIndices();await renderFreightCostPPI();await renderWorldBankPortTraffic();await renderUNCTADConnectivity();renderVoyageEstimator();renderPortWatchPermission();}else if(page==='commodities'){commodities();await renderOpenMacro();}else if(page==='shorts')shorts()}
init().catch(e=>{if($('v4app'))$('v4app').innerHTML=`<div class="sw-note sw-notice">Could not render this page: ${E(e.message)}</div>`;console.error(e)});
})();
