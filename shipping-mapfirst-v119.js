/* Stockwatch Shipping V119 — approved map-first maritime workspace.
 * IMPORTANT: moves the existing source-backed atlas to the first fold, never
 * removes its issuer/USDA/Eurostat/UNCTAD research modules. It does not
 * introduce a vessel-position feed or invent spot charter prices. */
(() => {
'use strict';
if(document.body.dataset.page!=='shipping')return;
const app=document.getElementById('v4app');
if(!app)return;
const NS='http://www.w3.org/2000/svg';
const research=[
 ['#offshoreRates','Offshore vessel & rig rates'],
 ['#usdaRouteRates','Published grain freight prices'],
 ['#nordicMaritime','Norway & European shipping'],
 ['#worldBankPortTraffic','Global container-port statistics'],
 ['#roroMarketTraffic','European Ro-Ro history'],
 ['#unctadConnectivity','Container-network connectivity'],
 ['#routeCompare','Compare freight routes'],
 ['#shippingBenchmarkAnchor','Vessel classes and route catalog'],
 ['#navprofitEconomics','Offshore charter economics calculator'],
 ['#voyageEstimator','Voyage cost scenario'],
 ['#shippingDataGuide','What shipping data means'],
 ['health.html','Data health and sources']
];
let mounted=false, portIndex=null, bordersLoading=false, atlasRef=null, guideRef=null, introRef=null;
const $=(p,id)=>p.querySelector(id);
function header(){
 const el=document.createElement('div');el.id='sw119Topbar';el.className='sw119-topbar';
 el.setAttribute('role','navigation');el.setAttribute('aria-label','Maritime atlas and Stockwatch navigation');
 el.innerHTML='<a class="sw119-brand" href="index.html" aria-label="Stockwatch overview"><i aria-hidden="true">⚓</i><span>stock<strong>watch</strong><small>MARITIME INTELLIGENCE</small></span></a>'+
 '<span class="sw119-top-divider" aria-hidden="true"></span><span class="sw119-section">Maritime Atlas</span>'+
 '<span class="sw119-status">SOURCE-BACKED EXPLORER</span>'+
 '<div class="sw119-top-links"><a href="index.html">Overview ↗</a><a href="stocks.html">Stocks ↗</a><a href="health.html">Data health ↗</a>'+
 '<details class="sw119-research-menu" id="sw119ResearchMenu"><summary class="sw119-research-toggle">Research <span aria-hidden="true">▾</span></summary>'+
 '<nav class="sw119-research-links" aria-label="Shipping research tools">'+
 research.map(([href,title])=>'<a href="'+href+'">'+title+'</a>').join('')+'</nav></details></div>';
 el.addEventListener('click',e=>{if(e.target.closest('.sw119-research-links a'))el.querySelector('details').open=false});
 return el;
}
function intro(){
 const el=document.createElement('section');el.id='sw119ResearchIntro';el.className='sw119-research-intro';
 el.innerHTML='<div><span class="sw-kicker">DATA DESK / RESEARCH & METHODOLOGY</span><h2>Explore the evidence behind the map</h2>'+
 '<p>Every figure has its own measurement, geography, source and period. Select a map point above, or open the full data series, company rates and scenario tools below. Old observations are kept visible with their original dates—not presented as live quotes.</p></div>'+
 '<nav class="sw119-research-shortcuts" aria-label="Full maritime research shortcuts">'+
 research.slice(0,10).map(([href,label])=>'<a href="'+href+'">'+label+' ↗</a>').join('')+'</nav>';
 return el;
}
const SVG=(tag,attrs={})=>{
 const n=document.createElementNS(NS,tag);
 for(const [key,value]of Object.entries(attrs))n.setAttribute(key,String(value));
 return n;
};
const pt=(lon,lat)=>[(lon+180)*900/360,(90-lat)*388/180];
function augmentGeography(atlas){
 const root=$ (atlas,'#shippingMapSvg');
 if(!root||$(root,'#sw119MaritimeGrid'))return;
 root.setAttribute('preserveAspectRatio','xMidYMid slice');
 const lineLayer=$(root,'#shippingMapLines');
 const grid=SVG('g',{id:'sw119MaritimeGrid','aria-hidden':'true'});
 for(let lon=-120;lon<=120;lon+=60){const x=pt(lon,0)[0];grid.append(SVG('line',{x1:x,y1:0,x2:x,y2:388}))}
 for(let lat=-60;lat<=60;lat+=30){const y=pt(0,lat)[1];grid.append(SVG('line',{x1:0,y1:y,x2:900,y2:y}))}
 const borders=SVG('g',{id:'sw119MaritimeBorders','aria-hidden':'true'});
 root.insertBefore(grid,lineLayer);root.insertBefore(borders,lineLayer);
 if(bordersLoading)return;
 bordersLoading=true;
 fetch('data/shipping-world-borders-v119.json',{cache:'force-cache'}).then(r=>{
  if(!r.ok)throw Error('Basemap boundary data unavailable');
  return r.json();
 }).then(d=>{
  if(d?.type!=='FeatureCollection'||d?.license!=='Public domain'||!Array.isArray(d.features))throw Error('Invalid public-domain geography');
  const paths=document.createDocumentFragment();
  for(const f of d.features){
   const g=f.geometry;
   if(!g||!['LineString','MultiLineString'].includes(g.type))continue;
   if(Number(f.properties?.min_zoom||0)>4)continue;
   const lines=g.type==='LineString'?[g.coordinates]:g.coordinates;
   let path='';
   for(const coords of lines){
    let prev=null;
    for(const pair of coords||[]){
     if(!Array.isArray(pair)||pair.length<2||!Number.isFinite(pair[0])||!Number.isFinite(pair[1])){prev=null;continue}
     const [x,y]=pt(pair[0],pair[1]);
     if(prev===null||Math.abs(x-prev)>450)path+='M'+x.toFixed(1)+' '+y.toFixed(1);
     else path+='L'+x.toFixed(1)+' '+y.toFixed(1);
     prev=x;
    }
   }
   if(path)paths.append(SVG('path',{d:path}));
  }
  if(borders.isConnected)borders.append(paths);
 }).catch(()=>{ /* Natural Earth land remains visible on source failure. */ });
}
function polishAtlas(atlas){
 atlas.classList.add('sw119-mapfirst');
 const h=$(atlas,'.sw-atlas-head');
 if(h){const title=$(h,'h2'),k=$(h,'.sw-kicker'),p=$(h,'p');
  if(k)k.textContent='THE GLOBAL SHIPPING ECONOMY / WORLD VIEW';
  if(title)title.textContent='One map. Every maritime market.';
  if(p)p.textContent='Explore the harbours, cargo networks, published shipping rates and offshore economics. Click a point to discover what the figures mean.';
 }
 const buttons={ports:'Ports & hubs',containers:'Cargo activity · TEU',roro:'Ro-Ro cargo',connectivity:'Liner networks',lanes:'Freight rates',ais:'Ships (AIS) · 0'};
 for(const [mode,label]of Object.entries(buttons)){
  const btn=atlas.querySelector('.sw-atlas-tab[data-layer="'+mode+'"]');
  if(btn)btn.textContent=label;
 }
 const toolbar=$(atlas,'.sw-atlas-toolbar');
 if(toolbar&&!$(atlas,'#sw119OffshoreRateLink')){
  const a=document.createElement('a');a.id='sw119OffshoreRateLink';
  a.href='#offshoreRates';a.className='sw119-offshore-tab';
  a.textContent='Offshore market ↗';toolbar.append(a);
 }
 const search=$(atlas,'#shippingMapSearch');
 if(search)search.placeholder='Port, country or freight route…';
 augmentGeography(atlas);
}
function footer(){
 const a=document.createElement('a');a.id='sw119BackMap';a.href='#shippingWorldMap';
 a.className='sw119-back-map';a.textContent='↑ Back to world map';
 document.body.append(a);
 const onScroll=()=>document.body.classList.toggle('sw119-away-from-map',scrollY>Math.max(400,innerHeight*.8));
 addEventListener('scroll',onScroll,{passive:true});onScroll();
}
const countryIso3={
 NO:'NOR',SE:'SWE',DK:'DNK',FI:'FIN',NL:'NLD',BE:'BEL',DE:'DEU',GB:'GBR',FR:'FRA',ES:'ESP',
 GR:'GRC',EG:'EGY',AE:'ARE',IN:'IND',LK:'LKA',SG:'SGP',CN:'CHN',KR:'KOR',JP:'JPN',
 US:'USA',CA:'CAN',BR:'BRA',ZA:'ZAF'
};
function loadPortIndex(){
 if(portIndex)return portIndex;
 portIndex=fetch('data/shipping-ports.json',{cache:'no-store'}).then(r=>{
  if(!r.ok)throw Error('World Bank unavailable');return r.json()
 }).then(d=>{
  if(!Array.isArray(d.series)||d.source?.sourceUrl!=='https://data.worldbank.org/indicator/IS.SHP.GOOD.TU')throw Error('Source identity mismatch');
  return new Map(d.series.filter(x=>x.unit==='TEU'&&x.frequency==='annual'&&/^\d{4}$/.test(x.period)&&Number.isFinite(x.value)&&x.value>0).map(x=>[x.countryCode,x]));
 }).catch(()=>new Map());
 return portIndex;
}
function inspectorUX(atlas){
 const panel=$(atlas,'#shippingMapInspector'),title=$(atlas,'#shippingMapDetailTitle');
 if(!panel||!title||$(atlas,'#sw119InspectorClose'))return;
 const close=document.createElement('button');close.type='button';close.id='sw119InspectorClose';
 close.className='sw119-inspector-close';close.setAttribute('aria-label','Close map details');
 close.textContent='×';panel.insertBefore(close,panel.firstChild);
 close.addEventListener('click',()=>{document.body.classList.remove('sw119-inspector-open');document.body.classList.add('sw119-inspector-hidden')});
 const actions=document.createElement('nav');actions.id='sw119DetailActions';actions.className='sw119-detail-actions';
 actions.setAttribute('aria-label','Related maritime research');
 panel.append(actions);
 const render=async()=>{
  const layer=atlas.querySelector('.sw-atlas-tab[aria-pressed="true"]')?.dataset.layer||'ports';
  const selected=$(atlas,'#shippingMapPick')?.value||'';
  let links=[];
  if(layer==='ports'){links=[['#worldBankPortTraffic','Country container activity ↗'],['#nordicMaritime','Regional shipping research ↗']]}
  else if(layer==='containers'){links=[['#worldBankPortTraffic','Container history & charts ↗'],['#nordicMaritime','Norway & Europe indicators ↗']]}
  else if(layer==='roro'){links=[['#roroMarketTraffic','Ro-Ro history and comparison ↗'],['#nordicMaritime','European shipping data ↗']]}
  else if(layer==='connectivity'){links=[['#unctadConnectivity','Liner connectivity history ↗'],['#shippingBenchmarkAnchor','Trade lanes and vessel classes ↗']]}
  else if(layer==='lanes'){links=[['#usdaRouteRates','Published freight rates ↗'],['#voyageEstimator','Model voyage cost ↗']]}
  else{links=[['#shippingDataGuide','Understand AIS & market data ↗'],['#offshoreRates','Offshore fleet dayrates ↗']]}
  actions.replaceChildren();
  if(layer==='ports'&&selected){
   const country=countryIso3[selected.split('-')[0]];
   const rows=await loadPortIndex();
   if($(atlas,'#shippingMapPick')?.value!==selected)return;
   const x=rows.get(country);
   if(x){
    const stat=document.createElement('div');stat.className='sw119-country-context';
    const strong=document.createElement('strong');strong.textContent=new Intl.NumberFormat('en-US',{maximumFractionDigits:0}).format(x.value);
    const label=document.createElement('small');
    label.textContent=x.label.replace(' container port throughput','')+' country total · TEU · '+x.period;
    const note=document.createElement('p');
    note.textContent='Published country container handling, NOT the selected port alone or current shipping demand.';
    stat.append(label,strong,note);actions.append(stat);
   }
  }
  for(const [href,label]of links){
   const a=document.createElement('a');a.href=href;a.textContent=label;
   actions.append(a);
  }
 };
 let updating=false;
 const schedule=()=>{if(updating)return;updating=true;requestAnimationFrame(()=>{updating=false;render()})};
 const obs=new MutationObserver(schedule);
 obs.observe(title,{childList:true,characterData:true,subtree:true});
 atlas.querySelectorAll('[data-layer]').forEach(b=>b.addEventListener('click',()=>{
  if(b.dataset.layer==='ais')document.body.classList.add('sw119-inspector-open');
  else document.body.classList.remove('sw119-inspector-open');
  schedule();
 }));
 const pick=$(atlas,'#shippingMapPick');
 if(pick)pick.addEventListener('change',()=>{if(pick.value){document.body.classList.add('sw119-inspector-open');document.body.classList.remove('sw119-inspector-hidden')}schedule()});
 const pins=$(atlas,'#shippingMapPins');
 if(pins)pins.addEventListener('click',e=>{if(e.target.closest('.sw-atlas-point')){document.body.classList.add('sw119-inspector-open');document.body.classList.remove('sw119-inspector-hidden');schedule()}});
 const lines=$(atlas,'#shippingMapLines');
 if(lines)lines.addEventListener('click',e=>{if(e.target.closest('.sw-atlas-lane')){document.body.classList.add('sw119-inspector-open');document.body.classList.remove('sw119-inspector-hidden');schedule()}});
 panel.addEventListener('click',e=>{if(e.target.closest('#sw119DetailActions a'))document.body.classList.remove('sw119-inspector-open')});
 if(innerWidth>900){
  let didSelect=false;
  const starter=new MutationObserver(()=>{
   if(didSelect)return;
   const target=$(atlas,'#shippingMapPick');
   if(target&&target.querySelector('option[value="NL-RTM"]')){
    didSelect=true;target.value='NL-RTM';target.dispatchEvent(new Event('change',{bubbles:true}));starter.disconnect();
   }
  });
  if(pick)starter.observe(pick,{childList:true});
  if(pick?.querySelector('option[value="NL-RTM"]')){didSelect=true;pick.value='NL-RTM';pick.dispatchEvent(new Event('change',{bubbles:true}));starter.disconnect()}
 }
 schedule();
}
function mount(){
 const atlas=app.querySelector('#shippingWorldMap')||atlasRef;
 if(!atlas)return;
 // V4 may rebuild #v4app while refreshing sources. Reattach the same
 // vetted map node and its controls to the new source-backed research DOM.
 if(!app.contains(atlas)&&!app.querySelector('#usdaRouteRates'))return;
 atlasRef=atlas;
 if(app.firstElementChild!==atlas)app.prepend(atlas);
 if(!mounted){
  mounted=true;
  document.body.classList.add('sw119-shipping-mapfirst');
  const top=header();app.parentElement.insertBefore(top,app);
  guideRef=$(atlas,'#shippingDataGuide');
  if(guideRef)atlas.insertAdjacentElement('afterend',guideRef);
  introRef=intro();
  (guideRef||atlas).insertAdjacentElement('afterend',introRef);
  footer();
  polishAtlas(atlas);inspectorUX(atlas);
 }else{
  if(guideRef&&guideRef.parentElement!==app)atlas.insertAdjacentElement('afterend',guideRef);
  if(introRef&&introRef.parentElement!==app)(guideRef||atlas).insertAdjacentElement('afterend',introRef);
 }
}
let waiting=false;
const observer=new MutationObserver(()=>{
 if(waiting)return;waiting=true;requestAnimationFrame(()=>{waiting=false;mount()});
});
observer.observe(app,{childList:true,subtree:false});
mount();
window.addEventListener('pagehide',()=>observer.disconnect(),{once:true});
})();