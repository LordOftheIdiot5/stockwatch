/* Stockwatch V118 — interactive global maritime atlas.
 * Geo-location points are APPROXIMATE reference anchors. Observational values
 * come only from the existing official dated source datasets. No simulated AIS.
 * The diagram is NOT a navigational or vessel-routing product. */
(() => {
'use strict';
if(document.body.dataset.page!=='shipping')return;
const app=document.getElementById('v4app');if(!app)return;
const NS='http://www.w3.org/2000/svg', W=900,H=388;
const F=new Intl.NumberFormat('en-US',{maximumFractionDigits:1});
const I=new Intl.NumberFormat('en-US',{maximumFractionDigits:0});
const U=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:2});
const Hesc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const legalUrl=x=>{try{const u=new URL(x,location.href);return u.protocol==='https:'?u.href:''}catch{return ''}};
const pos=(lon,lat)=>({x:(lon+180)*W/360,y:(90-lat)*H/180});
const svgNode=(tag,attrs={},label)=>{const n=document.createElementNS(NS,tag);for(const[k,v]of Object.entries(attrs))n.setAttribute(k,String(v));if(label!==undefined)n.textContent=String(label);return n};
const definitions={
 ports:{name:'Harbours',help:'Where selected maritime ports are located. Pins are approximate reference locations, not live ship positions or measured traffic for an individual harbour.',kind:'Infrastructure',unit:'Port-area locator'},
 containers:{name:'Containers',help:'Annual container handling by country (TEU). A TEU is the space of one 20-foot container; totals include empty and transshipped boxes. This is market activity, not demand, bookings or freight prices.',kind:'Country activity',unit:'TEU / year'},
 roro:{name:'Ro-Ro cargo',help:'Quarterly cargo weight handled by main ports for roll-on/roll-off transport. Values are country or EU aggregate totals, in thousand tonnes. Different reporting quarters cannot be read as the same session.',kind:'Regional cargo',unit:'thousand tonnes / quarter'},
 connectivity:{name:'Liner network',help:'UNCTAD monthly LSCI measures integration into scheduled container shipping networks. An index is not tonnes carried, a dayrate, transport demand, or USD.',kind:'Connectivity proxy',unit:'index (Q1 2023 = 100)'},
 lanes:{name:'Grain routes',help:'Two published USDA freight price observations for U.S. bulk grain routes to Japan. Dashed links are schematic origin/destination connections, not sailed paths or moving vessels.',kind:'Published freight',unit:'USD / metric tonne'},
 ais:{name:'Ship positions',help:'No permitted live AIS position source is connected to Stockwatch. No ship is plotted or guessed. Open an official traffic viewer or enable an authorized AIS integration in a later release.',kind:'AIS status',unit:'0 verified ship positions'}
};
const byCountry={China:'CHN','South Korea':'KOR',Singapore:'SGP','United States':'USA',Malaysia:'MYS',Germany:'DEU',Norway:'NOR',Sweden:'SWE',Denmark:'DNK',India:'IND',Japan:'JPN','United Kingdom':'GBR','United Arab Emirates':'ARE','Viet Nam':'VNM'};
const regions={
 global:'Global',
 nordic:'Nordic + North Sea',
 europe:'Europe',
 asia:'Asia + Middle East',
 americas:'Americas',
 africa:'Africa'
};
let loaded=null, mounted=false, activeUI=null;
function get(url){
 return fetch(url,{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()});
}
function sources(){
 if(!loaded)loaded=Promise.allSettled([
  get('data/shipping-world-atlas-v118.json'),
  get('data/shipping-ports.json'),
  get('data/shipping-roro-traffic.json'),
  get('data/shipping-connectivity.json'),
  get('data/shipping-usda-ocean-rates-s1.json')
 ]).then(x=>{
  const take=(n)=>x[n].status==='fulfilled'?x[n].value:null;
  const geo=take(0);
  if(!geo||geo.schemaVersion!==1||!Array.isArray(geo.ports)||geo.ports.length<25||!Array.isArray(geo.countryCenters))throw Error('Map anchor geometry unavailable');
  const centers=new Map(geo.countryCenters.map(p=>[p.iso3,p]));
  if(new Set(geo.ports.map(p=>p.id)).size!==geo.ports.length||geo.ports.some(p=>!Number.isFinite(p.lon)||!Number.isFinite(p.lat)||Math.abs(p.lat)>90||Math.abs(p.lon)>180))throw Error('Invalid reference geometry');
  const data={geo,centers,containers:take(1),roro:take(2),connectivity:take(3),lanes:take(4)};
  return data;
 });
 return loaded;
}
function html(){
 const s=document.createElement('section');s.id='shippingWorldMap';s.className='sw-panel sw-shipping-atlas';s.setAttribute('aria-labelledby','shippingAtlasTitle');
 s.innerHTML='<header class="sw-atlas-head"><div><span class="sw-kicker">MARITIME INTELLIGENCE / GLOBAL GEOGRAPHY</span><h2 id="shippingAtlasTitle">World shipping atlas</h2><p>Find ports, compare real cargo-activity observations, and follow published grain freight lanes. Choose a layer to see <strong>what the number measures</strong> and <strong>when it was reported</strong>.</p></div><a href="https://energy.nordl.dev/" target="_blank" rel="noopener noreferrer">Explore Energy Nordl ↗</a></header>'+
 '<div class="sw-atlas-legend" id="shippingMapLegend" aria-label="Map measurement type"><span class="sw-atlas-legend-key">Reference locations ≠ activity ≠ price ≠ ship location</span><span class="sw-atlas-asof">All values are source-dated, not live</span></div>'+
 '<div class="sw-atlas-toolbar" role="group" aria-label="Shipping map layers">'+Object.entries(definitions).map(([key,d])=>'<button class="sw-atlas-tab" type="button" data-layer="'+key+'" aria-pressed="'+(key==='ports'?'true':'false')+'">'+Hesc(d.name)+'</button>').join('')+'</div>'+
 '<div class="sw-atlas-controlbar"><label>Geography<select id="shippingMapRegion">'+Object.entries(regions).map(([k,v])=>'<option value="'+k+'">'+Hesc(v)+'</option>').join('')+'</select></label>'+
 '<label>Find a port, country or cargo<input id="shippingMapSearch" type="search" placeholder="Bergen, Singapore, Norway…" autocomplete="off"></label><label>Choose an observation<select id="shippingMapPick" aria-label="Select mapped observation"><option value="">Loading map points…</option></select></label></div>'+
 '<div class="sw-atlas-layout"><div class="sw-atlas-map-area"><div class="sw-atlas-mapbar"><span id="shippingMapCount" role="status">Preparing geographic layer…</span><div class="sw-atlas-zoom"><button type="button" data-map-zoom="in" aria-label="Zoom map in">+</button><button type="button" data-map-zoom="out" aria-label="Zoom map out">−</button><button type="button" data-map-zoom="reset" aria-label="Show whole world map">World</button></div></div>'+
 '<svg id="shippingMapSvg" class="sw-atlas-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 388" tabindex="0" role="group" aria-label="World shipping map. Use plus or minus for zoom, arrow keys to pan, Home to reset; select data points or use the nearby observation list.">'+
 '<rect width="900" height="388" fill="#081e30"/><image href="brand/world-land-ne110.svg" x="0" y="0" width="900" height="388" preserveAspectRatio="none" aria-hidden="true"/><g id="shippingMapLines"></g><g id="shippingMapPins"></g></svg>'+
 '<div class="sw-atlas-caption"><span><i class="sw-atlas-dot" aria-hidden="true"></i> Layer observations</span><span>No individual vessel positions without licensed AIS</span></div></div>'+
 '<aside class="sw-atlas-inspector" id="shippingMapInspector" aria-labelledby="shippingMapDetailTitle"><span class="sw-kicker">READ THE DATA</span><h3 id="shippingMapDetailTitle">Select a map point</h3><p id="shippingMapExplanation">Map reference points and original-source indicators are different things. Select any marker to see the measurement and original period.</p><div id="shippingMapFact"></div><p id="shippingMapSourceStatus" class="sw-atlas-source-state">No live ship tracking is connected.</p></aside></div>'+
 '<div class="sw-atlas-bottom"><p><strong>How to interpret the map:</strong> Country-level TEU and Ro-Ro pins are positioned as geographic labels; they do not imply a port-specific value. Prices are published route observations, not executable fixtures. The chart is an exploration tool, not a navigational map.</p><a href="https://www.kystverket.no/en/sea-transport-and-ports/ais/access-to-ais-data/" target="_blank" rel="noopener noreferrer">Norwegian official AIS access ↗</a><a href="https://vcps.nga.mil/nauticalpubs-feature/rest/services/WPI/World_Port_Index_Viewer/MapServer" target="_blank" rel="noopener noreferrer">World Port Index reference ↗</a></div>'+
 '<details class="sw-atlas-guide" id="shippingDataGuide"><summary>What do these shipping numbers actually mean?</summary><div class="sw-atlas-glossary">'+
 '<article><h4>USD/day — dayrate</h4><p>Money per vessel operating day, as reported by an issuer for a quarter. Not the current charter asking price, and not the company’s profit.</p></article>'+
 '<article><h4>USD/tonne — freight price</h4><p>Shipping cost per metric tonne of a specified cargo on a reported origin–destination trade lane. It cannot be compared directly to a vessel dayrate.</p></article>'+
 '<article><h4>TEU — container volume</h4><p>A 20-foot equivalent unit: a volume/handling measure, not cargo value, sales revenue, vessel count or a direct indicator of spot shipping demand.</p></article>'+
 '<article><h4>Ro-Ro — cargo weight</h4><p>Roll-on/roll-off cargo handled at main ports. Measured in thousands of tonnes per reporting quarter; countries can have different latest quarters.</p></article>'+
 '<article><h4>LSCI — network connectivity</h4><p>An index of scheduled liner-network integration. Higher index values do not directly equal container counts, freight prices or future shipping demand.</p></article>'+
 '<article><h4>AIS — ship location</h4><p>A timestamped individual ship-position message. Ship identity, coordinates, observation time and provider permissions must all be verified before plotting.</p></article>'+
 '</div><p>Port traffic, network connectivity, fleet utilization and contracts may help investigate shipping market supply and demand, but none alone proves market demand or predicts rates.</p></details>';
 return s;
}
function makeRows(data,mode){
 const rows=[];
 if(mode==='ports')return data.geo.ports.map(p=>({id:p.id,lon:p.lon,lat:p.lat,title:p.name,metric:'Port reference location',value:null,period:'No market observation',unit:'approximate port-area point',kind:'geography',region:p.region,sourceUrl:data.geo.referenceUrl,source:'World Port Index geographical reference',note:'Location only, not an AIS ship, port-throughput report or verified navigational berth.'}));
 if(mode==='ais'){
  if(!data.ais||!Array.isArray(data.ais.positions))return rows;
  for(const v of data.ais.positions){
   if(!Number.isInteger(v.mmsi)||!Number.isFinite(v.longitude)||!Number.isFinite(v.latitude))continue;
   const title=v.name||('MMSI '+v.mmsi);
   rows.push({id:'vessel:'+v.mmsi,lon:v.longitude,lat:v.latitude,title,
    metric:'AIS reported vessel position · '+v.mmsi+' · '+(v.destinationAisReported||'destination unknown'),
    value:null,period:v.positionReportedAt,unit:'latitude / longitude',kind:'vessel',
    region:v.latitude>=53&&v.latitude<=72&&v.longitude>=4&&v.longitude<=33?'nordic':'europe',
    sourceUrl:data.ais.sourceUrl,source:'Fintraffic Digitraffic · CC BY 4.0',
    note:'Last reported AIS point, not a navigable route, ship owner, cargo, verified destination or guaranteed current location.',
    vessel:v});
  }
  return rows;
 }
 const c=data.centers;
 if(mode==='containers'){
  const d=data.containers;
  if(!d||!Array.isArray(d.series)||!d.source?.sourceUrl)return rows;
  for(const x of d.series){
   if(x.unit!=='TEU'||x.frequency!=='annual'||!Number.isFinite(x.value)||x.value<0||!/^\d{4}$/.test(x.period))continue;
   const p=c.get(x.countryCode);if(!p)continue;
   rows.push({id:'container:'+x.countryCode,lon:p.lon,lat:p.lat,title:x.label.replace(/ container port throughput$/,''),metric:'Country container-port throughput',value:x.value,period:x.period,unit:'TEU / year',kind:'activity',region:regionFor(p.iso3),sourceUrl:x.sourceUrl||d.source.sourceUrl,source:x.provider||'World Bank / UNCTAD',note:'Annual country aggregate, not a number for the harbour at the marker. Includes empty/transshipment containers; no comparison with daily charter quotes.'});
  }
 }
 if(mode==='roro'){
  const d=data.roro;if(!d||d.provider!=='Eurostat'||d.datasetCode!=='mar_go_qmc'||!Array.isArray(d.series))return rows;
  const map={NO:'NOR',SE:'SWE',DK:'DNK',NL:'NLD',DE:'DEU',BE:'BEL',FI:'FIN',FR:'FRA',ES:'ESP',EU27_2020:'EU27_2020'};
  for(const x of d.series){
   if(x.unit!=='thousand tonnes'||x.frequency!=='quarterly'||!Number.isFinite(x.value)||x.value<0||!/^\d{4}-Q[1-4]$/.test(x.period))continue;
   const p=c.get(map[x.countryCode]);if(!p)continue;
   rows.push({id:'roro:'+x.countryCode,lon:p.lon,lat:p.lat,title:x.label,metric:'Ro-Ro cargo at main ports',value:x.value,period:x.period,unit:'thousand tonnes / quarter',kind:'activity',region:regionFor(p.iso3),sourceUrl:d.sourceUrl,source:'Eurostat mar_go_qmc',note:'Country/region aggregate, not an individual port value. EU-27 includes member-country values: never sum the aggregate with countries.'});
  }
 }
 if(mode==='connectivity'){
  const d=data.connectivity;if(!d||!Array.isArray(d.series))return rows;
  for(const x of d.series){
   const p=c.get(byCountry[x.country]);if(!p||!Number.isFinite(x.value)||x.value<0||!/^\d{4}-\d{2}$/.test(x.period)||!String(x.unit).includes('index'))continue;
   rows.push({id:'liner:'+x.country,lon:p.lon,lat:p.lat,title:x.country,metric:'Monthly liner shipping connectivity index',value:x.value,period:x.period,unit:'LSCI index',kind:'index',region:regionFor(p.iso3),sourceUrl:d.source.sourceUrl,source:'UNCTAD Data Hub',note:'Network integration index with Q1 2023 average baseline. Not boxes handled, vessel count, physical shipping demand or a price.'});
  }
 }
 if(mode==='lanes'){
  const d=data.lanes;if(!d||d.unit!=='USD/metric_ton'||!Array.isArray(d.rates)||!d.sourceUrl||d.isExecutableQuote!==false)return rows;
  const anchors=[{from:[-90.1,29.1],to:[139.7,35.5],name:'U.S. Gulf → Japan'},
   {from:[-123.2,46.1],to:[139.7,35.5],name:'Pacific Northwest → Japan'}];
  for(const x of d.rates){
   const a=anchors.find(v=>v.name===x.route);
   if(!a||!Number.isFinite(x.value)||x.value<=0||x.unit!=='USD/metric_ton')continue;
   rows.push({id:x.id,title:x.route,metric:'USDA published bulk-grain ocean freight',value:x.value,period:x.observationDate,unit:'USD / metric tonne',kind:'freight',region:'global',lon:a.from[0],lat:a.from[1],to:a.to,from:a.from,sourceUrl:d.sourceUrl,source:d.source+' — '+d.report, note:'Schematic origin–destination trade lane. This is a documented freight-price indication, not a physical sailed route, vessel observation, executable contract or container price.'});
  }
 }
 return rows;
}
function regionFor(code){
 if(['NOR','SWE','DNK','FIN'].includes(code))return 'nordic';
 if(['NLD','DEU','GBR','BEL','FRA','ESP','EU27_2020'].includes(code))return 'europe';
 if(['CHN','SGP','JPN','KOR','IND','ARE','VNM','MYS'].includes(code))return 'asia';
 if(['USA'].includes(code))return 'americas';
 return 'global';
}
function filterRow(r,region){
 if(region==='global')return true;
 if(region==='europe')return r.region==='europe'||r.region==='nordic';
 if(region==='nordic')return r.region==='nordic'||(r.region==='europe'&&['Rotterdam','Hamburg','Antwerp','Bremerhaven','Felixstowe'].includes(r.title));
 if(region==='asia')return r.region==='asia'||r.region==='middle-east';
 return r.region===region;
}
function frame(){
 const state={mode:'ports',region:'global',q:'',selected:null,view:[0,0,W,H],rows:[],data:null,aisStatus:'not_enabled'};
 const el=html();
 const select=el.querySelector('#shippingMapPick'),search=el.querySelector('#shippingMapSearch'),area=el.querySelector('#shippingMapRegion');
 const map=el.querySelector('#shippingMapSvg'),pins=el.querySelector('#shippingMapPins'),lines=el.querySelector('#shippingMapLines');
 const count=el.querySelector('#shippingMapCount'),title=el.querySelector('#shippingMapDetailTitle'),explain=el.querySelector('#shippingMapExplanation'),fact=el.querySelector('#shippingMapFact'),sourceState=el.querySelector('#shippingMapSourceStatus');
 function showView(){
  const [x,y,w,h]=state.view;
  map.setAttribute('viewBox',[x,y,w,h].map(n=>Number(n.toFixed(2))).join(' '));
 }
 function zoom(f){
  const [x,y,w,h]=state.view,newW=Math.max(150,Math.min(W,w*f)),newH=newW*H/W,cx=x+w/2,cy=y+h/2;
  state.view=[Math.max(0,Math.min(W-newW,cx-newW/2)),Math.max(0,Math.min(H-newH,cy-newH/2)),newW,newH];showView();
 }
 function pan(dx,dy){
  const [x,y,w,h]=state.view;
  state.view=[Math.max(0,Math.min(W-w,x+dx)),Math.max(0,Math.min(H-h,y+dy)),w,h];showView();
 }
 function selectRow(id){
  state.selected=id;
  select.value=id||'';
  const r=state.rows.find(x=>x.id===id);
  const info=definitions[state.mode];
  if(!r){
   title.textContent=state.mode==='ais'?(state.aisStatus==='available'?'Select an AIS-reported vessel':'No live AIS feed connected'):'Choose a '+info.kind.toLowerCase()+' point';
   explain.textContent=info.help;
   fact.replaceChildren();
   sourceState.textContent=state.mode==='ais'?(state.aisStatus==='loading'?'Checking source-dated AIS observations…':state.aisStatus==='available'?'Fintraffic / digitraffic.fi · CC BY 4.0 · partial coverage.':state.aisStatus==='unavailable'?'AIS source temporarily unavailable or stale; no positions displayed.':'Ship positions available: 0. Official feeds require verifiable credentials/permissions and timestamps.'):'Select a marker or use the observation list. Historical measurements are not live market quotes.';
   pins.querySelectorAll('.sw-atlas-point').forEach(p=>p.classList.remove('selected'));
   return;
  }
  title.textContent=r.title;explain.textContent=r.metric;
  fact.replaceChildren();
  const details=document.createElement('div');details.className='sw-atlas-factgrid';
  const add=(a,b)=>{const k=document.createElement('span'),v=document.createElement('strong');k.textContent=a;v.textContent=b;details.append(k,v)};
  if(r.kind==='vessel'){
   const v=r.vessel;
   add('Vessel identity','MMSI '+v.mmsi+(v.imo?' · IMO '+v.imo:''));
   add('Ship class',v.vesselClass||'Unclassified');
   add('AIS position reported',v.positionReportedAt);
   add('Coordinates',v.latitude.toFixed(4)+'°, '+v.longitude.toFixed(4)+'°');
   add('Speed over ground',v.speedKnots===null?'Not reported':v.speedKnots+' kn');
   add('Course over ground',v.courseDegrees===null?'Not reported':v.courseDegrees+'°');
   add('AIS-reported destination',v.destinationAisReported||'Not reported / unverified');
   add('Identity metadata reported',v.metadataReportedAt||'Timestamp unavailable');
  }else{
   if(r.value!==null)add('Reported figure',r.kind==='freight'?U.format(r.value):r.kind==='index'?F.format(r.value):I.format(r.value));
   add('Unit / scale',r.unit);add('Observed period',r.period);add('Category',r.kind==='geography'?'Reference location':r.kind==='freight'?'Published route freight':r.kind==='index'?'Network connectivity':'Regional cargo activity');
  }
  fact.append(details);
  const description=document.createElement('p');description.textContent=r.note;fact.append(description);
  const link=document.createElement('a');const url=legalUrl(r.sourceUrl);if(url){link.href=url;link.target='_blank';link.rel='noopener noreferrer';link.textContent='Open original source ↗';fact.append(link)}
  sourceState.textContent=r.kind==='vessel'?'Source: Fintraffic Digitraffic (CC BY 4.0). Reported AIS position, not continuously live or a verified itinerary.':r.source+'. Source and observation date shown above. Geographic anchor location may be approximate.';
  pins.querySelectorAll('.sw-atlas-point').forEach(p=>p.classList.toggle('selected',p.dataset.id===id));
 }
 function laneDraw(r){
  const a=pos(r.from[0],r.from[1]),b=pos(r.to[0],r.to[1]);
  let bx=b.x;
  if(bx-a.x>W/2)bx-=W;
  else if(bx-a.x<-W/2)bx+=W;
  for(const shift of [-W,0,W]){
   const x1=a.x+shift,x2=bx+shift;
   const curve=svgNode('path',{d:'M '+x1+' '+a.y+' Q '+((x1+x2)/2)+' '+(Math.min(a.y,b.y)-28)+' '+x2+' '+b.y,
    class:'sw-atlas-lane',role:'button',tabindex:'0','aria-label':r.title+', published '+r.period,'data-id':r.id});
   const choose=()=>selectRow(r.id);
   curve.addEventListener('click',choose);
   curve.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose()}});
   lines.append(curve);
  }
 }
 function draw(){
  if(!state.data)return;
  pins.replaceChildren();lines.replaceChildren();
  const all=makeRows(state.data,state.mode);
  state.rows=all.filter(r=>filterRow(r,state.region)&&(!state.q||(r.title+' '+r.metric+' '+r.unit).toLowerCase().includes(state.q)));
  const hasData=all.length>0;
  count.textContent=state.mode==='ais'?(state.aisStatus==='available'?state.rows.length+' timestamped vessel positions · Fintraffic partial coverage':state.aisStatus==='loading'?'Checking AIS source…':state.aisStatus==='unavailable'?'AIS feed unavailable or stale · 0 positions':'0 verified vessel positions · AIS connection required'):state.rows.length+' map '+(state.rows.length===1?'observation':'observations')+' · '+definitions[state.mode].kind+' · original reporting dates';
  select.replaceChildren();
  const blank=document.createElement('option');blank.value='';blank.textContent=state.rows.length?'Select a mapped item…':hasData?'No matches in this area':'No measured observations connected';select.append(blank);
  for(const r of state.rows){
   const o=document.createElement('option');o.value=r.id;o.textContent=r.title+(r.value===null?' · port anchor':' · '+r.period);select.append(o);
   if(state.mode==='lanes')laneDraw(r);
   const p=pos(r.lon,r.lat),c=svgNode('circle',{
    cx:p.x,cy:p.y,r:r.kind==='geography'?4.3:r.kind==='vessel'?5.1:6.2,
    class:'sw-atlas-point sw-atlas-'+r.kind,'data-id':r.id,
    role:'button',tabindex:'0','aria-label':r.title+'. '+r.metric+'. '+r.period
   });
   c.append(svgNode('title',{},r.title));
   const act=()=>selectRow(r.id);
   c.addEventListener('click',act);c.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();act()}});
   pins.append(c);
   if(r.kind==='freight'){
    const dest=pos(r.to[0],r.to[1]);pins.append(svgNode('circle',{cx:dest.x,cy:dest.y,r:4.2,class:'sw-atlas-destination'}));
   }
  }
  if(state.selected&&!state.rows.some(r=>r.id===state.selected))state.selected=null;
  selectRow(state.selected);
  const stat=el.querySelector('#shippingMapLegend .sw-atlas-asof');
  stat.textContent=state.mode==='ports'?'40 approximate reference ports · no local throughput assigned':
   state.mode==='ais'?(state.aisStatus==='available'?'Fintraffic CC BY 4.0 · timestamped positions, not simulated tracks':state.aisStatus==='unavailable'?'Fintraffic source unavailable · no stale vessel pins':'No AIS feed — ship positions are not simulated'):
   state.mode==='containers'?'Annual country container totals — last known published years':
   state.mode==='roro'?'Quarterly country / EU Ro-Ro cargo weights':
   state.mode==='connectivity'?'Monthly liner network index, not vessel demand':
   'Two USDA grain freight observations, dated and unit-labelled';
  el.querySelectorAll('[data-layer]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.layer===state.mode)));
  const aisTab=el.querySelector('.sw-atlas-tab[data-layer="ais"]');
  if(aisTab)aisTab.textContent='Ships (AIS) · '+(state.aisStatus==='available'?state.rows.length:0);
  const aisCaption=el.querySelector('.sw-atlas-caption span:last-child');
  if(aisCaption)aisCaption.textContent=state.mode==='ais'&&state.aisStatus==='available'?'Fintraffic · last-reported positions · partial coverage':'No individual vessel positions without licensed AIS';
 }
 let aisRequested=false;
 async function loadAis(){
  if(aisRequested||!state.data)return;
  aisRequested=true;state.aisStatus='loading';draw();
  try{
   const configRes=await fetch('data/shipping-ais-v120-config.json',{cache:'no-store'});
   if(!configRes.ok)throw Error('AIS configuration absent');
   const config=await configRes.json();
   if(config?.schemaVersion!==1||config?.enabled!==true){
    state.aisStatus='not_enabled';draw();return;
   }
   const endpoint=new URL(config.endpoint,location.href);
   if(endpoint.protocol!=='https:'||endpoint.pathname!=='/api/marine/vessels'||
     !(endpoint.origin===location.origin||endpoint.hostname.endsWith('.workers.dev')))
    throw Error('Unapproved AIS endpoint');
   const response=await fetch(endpoint.href,{cache:'no-store',mode:'cors'});
   if(!response.ok)throw Error('AIS source unavailable');
   const payload=await response.json();
   const now=Date.now();
   if(payload?.schemaVersion!==1||payload.sourceId!=='fintraffic-ais-v1'||
    payload.provider!=='Fintraffic Digitraffic'||payload.license!=='CC BY 4.0'||
    !Array.isArray(payload.positions)||payload.positions.length>2500||
    !Number.isFinite(Date.parse(payload.retrievedAt))||
    Date.parse(payload.retrievedAt)>now+120000||
    now-Date.parse(payload.retrievedAt)>10*60000)throw Error('Invalid AIS snapshot');
   const seen=new Set();
   const valid=payload.positions.filter(v=>{
    if(!v||!Number.isInteger(v.mmsi)||v.mmsi<100000000||v.mmsi>999999999||
      !Number.isFinite(v.longitude)||!Number.isFinite(v.latitude)||
      Math.abs(v.longitude)>180||Math.abs(v.latitude)>90||seen.has(v.mmsi))return false;
    const t=Date.parse(v.positionReportedAt);
    if(!Number.isFinite(t)||t>now+120000||now-t>30*60000)return false;
    if(v.name!==null&&typeof v.name!=='string')return false;
    seen.add(v.mmsi);return true;
   });
   if(!valid.length)throw Error('No fresh verified AIS positions');
   state.data.ais={...payload,positions:valid};
   state.aisStatus='available';
  }catch(error){
   state.aisStatus='unavailable';
   state.data.ais=null;
  }
  if(state.mode==='ais')draw();
 }
 el.querySelectorAll('[data-layer]').forEach(b=>b.addEventListener('click',()=>{
  state.mode=b.dataset.layer;state.q='';search.value='';state.selected=null;draw();
  if(state.mode==='ais')loadAis();
 }));
 area.addEventListener('change',()=>{state.region=area.value;state.selected=null;draw()});
 search.addEventListener('input',()=>{state.q=search.value.trim().toLowerCase();state.selected=null;draw()});
 select.addEventListener('change',()=>selectRow(select.value||null));
 el.querySelectorAll('[data-map-zoom]').forEach(b=>b.addEventListener('click',()=>{
  if(b.dataset.mapZoom==='reset'){state.view=[0,0,W,H];showView()}else zoom(b.dataset.mapZoom==='in'?.74:1/.74);
 }));
 map.addEventListener('wheel',e=>{e.preventDefault();zoom(e.deltaY>0?1.22:.82)},{passive:false});
 map.addEventListener('keydown',e=>{
  if(e.target!==map)return;
  if(['+','=','-','Home','ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){
   e.preventDefault();
   if(e.key==='Home'){state.view=[0,0,W,H];showView()}
   else if(e.key==='+'||e.key==='=')zoom(.75);
   else if(e.key==='-')zoom(1/.75);
   else pan((e.key==='ArrowRight'?1:e.key==='ArrowLeft'?-1:0)*state.view[2]*.10,(e.key==='ArrowDown'?1:e.key==='ArrowUp'?-1:0)*state.view[3]*.10);
  }
 });
 let drag=null;
 map.addEventListener('pointerdown',e=>{if(e.button!==0||e.target.closest('.sw-atlas-point,.sw-atlas-lane'))return;drag={id:e.pointerId,cx:e.clientX,cy:e.clientY,from:state.view.slice(),moved:false};try{map.setPointerCapture(e.pointerId)}catch{}});
 map.addEventListener('pointermove',e=>{
  if(!drag||drag.id!==e.pointerId)return;
  const dx=e.clientX-drag.cx,dy=e.clientY-drag.cy;if(!drag.moved&&Math.hypot(dx,dy)<5)return;drag.moved=true;
  const [, , w,h]=drag.from,box=map.getBoundingClientRect();
  state.view=[Math.max(0,Math.min(W-w,drag.from[0]-dx*w/(box.width||1))),Math.max(0,Math.min(H-h,drag.from[1]-dy*h/(box.height||1))),w,h];
  showView();
 });
 const done=e=>{if(drag?.id===e.pointerId)drag=null};
 for(const ev of ['pointerup','pointercancel','lostpointercapture'])map.addEventListener(ev,done);
 return {el,setData(d){state.data=d;draw()},state};
}
function mount(){
 if(app.querySelector('#shippingWorldMap'))return;
 const anchor=app.querySelector('#usdaRouteRates');if(!anchor)return;
 // V4 can refresh the entire research app after initial async ingestion.
 // Keep the original interactive map node with its fetched real data and
 // listeners instead of leaving the page without an atlas on refresh.
 if(mounted&&activeUI){anchor.insertAdjacentElement('afterend',activeUI.el);return;}
 mounted=true;const ui=frame();activeUI=ui;
 anchor.insertAdjacentElement('afterend',ui.el);
 sources().then(d=>ui.setData(d)).catch(()=>{ui.el.querySelector('#shippingMapCount').textContent='Map reference data temporarily unavailable.';ui.el.querySelector('#shippingMapExplanation').textContent='Source errors are visible; the original rates and regional indicators remain available elsewhere on Shipping.';ui.el.querySelector('#shippingMapPick').replaceChildren(new Option('No verified map observations available',''))});
}
let queued=false;
const obs=new MutationObserver(()=>{if(!queued){queued=true;requestAnimationFrame(()=>{queued=false;mount()})}});
obs.observe(app,{childList:true,subtree:true});mount();
window.addEventListener('pagehide',()=>obs.disconnect(),{once:true});
})();