/* V121 Shipping market evidence desk.
 * Reads already-published Stockwatch source snapshots, not live broker/AIS
 * feeds. No simulated records, causal claims, trading signals or forecasts.
 */
import {buildMaritimePulse,valuePercent} from './scripts/maritime-pulse-v121.mjs';
if(document.body.dataset.page==='shipping'){
 const dataPaths={
  freight:'data/shipping-open.json',
  connectivity:'data/shipping-connectivity.json',
  roro:'data/shipping-roro-traffic.json',
  ports:'data/shipping-ports.json',
  company:'data/company-operating-metrics.json',
  rates:'data/shipping-usda-ocean-rates-s1.json'
 };
 const $=(x,s)=>x.querySelector(s);
 const el=(tag,cls,text)=>{
  const node=document.createElement(tag);
  if(cls)node.className=cls;
  if(text!==undefined)node.textContent=String(text);
  return node;
 };
 const percent=x=>x===null?'Not comparable':valuePercent(x);
 const fmt=x=>typeof x==='number'?x.toLocaleString('en-US',{maximumFractionDigits:x<1000?2:0}):'—';
 const host=document.getElementById('v4app');
 let root=null,peek=null,loading=false,loaded=false,lastData=null,currentFilter='all';
 const sourceStatus=el('p','sw121-status','Reading source-dated datasets…');
 sourceStatus.id='sw121SourceStatus';
 sourceStatus.setAttribute('role','status');
 const cards=el('div','sw121-card-grid');cards.id='sw121SignalCards';
 const title=el('h2','', 'What changed in maritime markets?');
 const introduction=el('p','sw121-intro','Evidence from published source series, not a live exchange tape. Compare like periods, inspect original units, and follow the map or company research without assuming causation.');
 const section=el('section','sw121-market-pulse');
 section.id='sw121MarketPulse';
 section.setAttribute('aria-labelledby','sw121MarketPulseTitle');
 title.id='sw121MarketPulseTitle';
 const top=el('div','sw121-title-row');
 const heading=el('div','sw121-title-copy');
 heading.append(el('span','sw121-kicker','MARKET INTELLIGENCE / SOURCE-DATED'),title,introduction);
 const refresh=el('button','sw121-refresh','Recheck published data');
 refresh.type='button';
 refresh.addEventListener('click',()=>load(true));
 top.append(heading,refresh);
 const controls=el('div','sw121-filters');
 controls.setAttribute('role','group');
 controls.setAttribute('aria-label','Filter market observations');
 const filters=[['all','All observations'],['ocean_cost','Freight costs'],['liner_connectivity','Networks'],['roro_cargo','Cargo'],['issuer_operating','Companies'],['freight_indications','Rate indications'],['container_handling','Long-term']];
 for(const [id,label] of filters){
  const b=el('button','sw121-filter',label);b.type='button';b.dataset.filter=id;
  b.setAttribute('aria-pressed',id==='all'?'true':'false');
  b.addEventListener('click',()=>{
   currentFilter=id;
   controls.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));
   if(lastData)render(lastData);
  });
  controls.append(b);
 }
 const notes=el('p','sw121-methodology','Only source-compatible comparisons are shown. Quarterly Ro-Ro is compared with the same quarter last year; historical throughput is clearly dated. No daily Baltic quotations, continuous AIS or verified forward earnings are connected.');
 section.append(top,sourceStatus,controls,cards,notes);
 function context(s){
  const focus=s.focus;
  if(!focus)return null;
  const a=el('button','sw121-map-context',focus.layer==='lanes'?'Open freight layer ↗':focus.preset==='world'?'See world geography ↗':'Show geographic context ↗');
  a.type='button';
  a.addEventListener('click',()=>{
   const atlas=document.getElementById('shippingWorldMap');
   if(!atlas)return;
   if(focus.layer){
    const button=atlas.querySelector('[data-layer="'+focus.layer+'"]');
    if(button)button.click();
   }else{
    const map=atlas.querySelector('#shippingMapSvg');
    if(map)map.dispatchEvent(new CustomEvent('sw119-map-focus',{detail:focus}));
   }
   atlas.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth',block:'start'});
  });
  return a;
 }
 function makeCard(signal){
  const article=el('article','sw121-signal-card');article.dataset.signal=signal.id;
  const kicker=el('div','sw121-card-meta');
  kicker.append(el('span','sw121-card-type',signal.type.replace(/_/g,' ')),
                el('span','sw121-card-period',signal.period+(signal.historical?' · Historical':'')));
  const h=el('h3','',signal.title);
  const summary=el('p','sw121-signal-summary',signal.headline);
  article.append(kicker,h,summary);
  const table=el('div','sw121-measures');
  for(const f of signal.figures){
   const line=el('div','sw121-measure');
   const label=el('span','sw121-measure-label',f.label);
   const value=el('strong','sw121-measure-value',
    fmt(f.value)+' '+f.unit);
   const delta=el('span','sw121-measure-delta',
    signal.kind==='observed_comparison'?percent(f.changePct):'Observed level');
   if(signal.kind==='observed_comparison'&&f.changePct!==null){
    delta.dataset.direction=f.changePct>0?'up':f.changePct<0?'down':'flat';
    delta.setAttribute('aria-label',percent(f.changePct)+' versus '+(
     signal.comparison==='same_quarter_prior_year'?'same quarter last year':
     signal.comparison==='prior_quarter'?'preceding quarter':
     signal.comparison==='prior_year'?'previous year':
     signal.comparison==='previous_month'?'previous month':'previous week'));
   }
   line.append(label,value,delta);table.append(line);
  }
  article.append(table);
  const caveat=el('p','sw121-caveat',signal.caveat);
  article.append(caveat);
  const footer=el('div','sw121-card-footer');
  const url=signal.sourceUrl;
  try{
   const parsed=new URL(url);
   if(parsed.protocol==='https:'){
    const source=el('a','sw121-source-link','Original source ↗');
    source.href=parsed.href;source.rel='noopener noreferrer';source.target='_blank';
    source.title=signal.source;
    footer.append(source);
   }
  }catch{/* No invented source link. */}
  if(typeof signal.companyUrl==='string'&&signal.companyUrl.startsWith('company.html?ticker=')){
   const company=el('a','sw121-company-link','Company research ↗');
   company.href=signal.companyUrl;footer.append(company);
  }
  const map=context(signal);if(map)footer.append(map);
  article.append(footer);
  article.append(el('p','sw121-source-line','Source: '+signal.source+' · Period '+signal.period));
  return article;
 }
 function render(data){
  lastData=data;
  const shown=currentFilter==='all'?data.signals:data.signals.filter(x=>x.type===currentFilter);
  cards.replaceChildren(...shown.map(makeCard));
  if(!shown.length)cards.append(el('p','sw121-empty',data.signalCount?
   'No source-backed observations in this category. Choose another filter.':
   'No compatible, sufficiently recent source observations are currently available. Historical research remains accessible below.'));
  const count=data.signalCount;
  sourceStatus.textContent=count+' source-dated observation '+(count===1?'group':'groups')+
   ' · Calculated from stored datasets · Not a live market or vessel tracker';
  if(peek){
   peek.textContent='';
   peek.append(el('strong','',count?'Market pulse · '+count+' observations':'Market pulse · Sources unavailable'));
   peek.append(el('span','',count?'Compare freight, cargo and connectivity ↘':'Read the data status ↘'));
  }
 }
 async function fetchSource(path){
  const response=await fetch(path+'?pulse=v121',{cache:'no-store'});
  if(!response.ok)throw Error('source_http_'+response.status);
  const json=await response.json();
  if(!json||typeof json!=='object'||Array.isArray(json))throw Error('invalid_source_payload');
  return json;
 }
 async function load(force=false){
  if(loading||loaded&&!force)return;
  loading=true;refresh.disabled=true;
  sourceStatus.textContent='Checking the latest stored source snapshots…';
  try{
   const names=Object.keys(dataPaths);
   const completed=await Promise.allSettled(names.map(name=>fetchSource(dataPaths[name])));
   const dataset={};
   let failures=0;
   completed.forEach((result,i)=>{
    if(result.status==='fulfilled')dataset[names[i]]=result.value;
    else failures++;
   });
   const pulse=buildMaritimePulse(dataset);
   render(pulse);
   if(failures)sourceStatus.textContent+=' · '+failures+' dataset '+(failures===1?'unavailable':'sources unavailable');
   loaded=true;
  }catch{
   sourceStatus.textContent='Market pulse temporarily unavailable. Original historical shipping research remains accessible below.';
   cards.replaceChildren(el('p','sw121-empty','Unable to verify source-dated market observations; no comparison has been invented.'));
   if(peek)peek.textContent='Market pulse · Temporarily unavailable';
  }finally{loading=false;refresh.disabled=false;}
 }
 function mount(){
  if(!host)return;
  const atlas=document.getElementById('shippingWorldMap');
  if(!atlas||!host.contains(atlas))return;
  if(atlas.nextElementSibling!==section)atlas.insertAdjacentElement('afterend',section);
  if(!peek){
   peek=el('a','sw121-map-peek','Market pulse · Checking sources');
   peek.href='#sw121MarketPulse';
   peek.setAttribute('aria-label','Open source-dated shipping market observations');
   atlas.append(peek);
  }else if(peek.parentElement!==atlas)atlas.append(peek);
  const menu=document.querySelector('#sw119Topbar .sw119-research-links');
  if(menu&&!menu.querySelector('a[href="#sw121MarketPulse"]')){
   const link=el('a','','What changed? · Market pulse');
   link.href='#sw121MarketPulse';menu.prepend(link);
  }
  if(!loaded&&!loading)load();
 }
 let queued=false;
 const observer=new MutationObserver(()=>{
  if(queued)return;queued=true;
  requestAnimationFrame(()=>{queued=false;mount()});
 });
 if(host)observer.observe(host,{childList:true,subtree:false});
 mount();
}
