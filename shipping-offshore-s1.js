/* Shipping S1 — Q3 2026 issuer-reported operating rates, not a live broker rate feed. */
(() => {
'use strict';
if(document.body.dataset.page!=='shipping')return;
const host=document.getElementById('v4app');
if(!host)return;
const USD=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0});
const PCT=new Intl.NumberFormat('en-US',{maximumFractionDigits:1,minimumFractionDigits:1,signDisplay:'always'});
const H=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const Q=x=>String(x).replace(/^(\d{4})-Q([1-4])$/,'Q$2 $1');
let loaded=null,scheduled=false;
function load(){
 if(!loaded)loaded=fetch('data/offshore-rate-evidence-v117s.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()}).then(d=>{
   if(d.schemaVersion!==1||d.brokerSpotRatesLicensed!==0||!Array.isArray(d.observations)||d.observations.length<10||!Array.isArray(d.sources)||d.sources.length<3)throw Error('Invalid evidence version or source status');
   const src=new Map(d.sources.map(s=>[s.id,s]));
   const ids=new Set();
   for(const r of d.observations){
    if(ids.has(r.id)||!src.has(r.sourceId)||!(r.value>0)||!Number.isFinite(r.value)||r.unit!=='USD/day'||r.isBrokerSpotQuote!==false||r.rateType!=='issuer_reported_quarterly_average'||!r.periodEnd||!r.vesselClass||!r.rateBasis)throw Error('Invalid or duplicated source record');
    ids.add(r.id);
   }
   return {d,src};
 });
 return loaded;
}
function create(){
 const n=document.createElement('section');n.id='offshoreRates';n.className='sw-panel sw-offshore';
 n.setAttribute('aria-labelledby','offshoreRatesTitle');
 n.innerHTML='<header class="sw-offshore-head"><div><span class="sw-kicker">OFFSHORE INTELLIGENCE / SOURCE-DATED PRICES</span><h2 id="offshoreRatesTitle">Real vessel and rig dayrates</h2><p>Reported operating averages from original company results. Actual USD/day figures, never invented broker spot prices.</p></div><a href="research.html#history-evidence">Methodology ↗</a></header>'+
 '<div class="sw-offshore-status" id="offshoreStatus" role="status">Loading verified original-company observations…</div>'+
 '<div class="sw-offshore-highlights" id="offshoreHighlights"></div>'+
 '<div class="sw-offshore-controls" id="offshoreControls" hidden><label>Vessel class<select id="offshoreSegment"><option value="all">All classes</option></select></label><label>Issuer<select id="offshoreIssuer"><option value="all">All issuers</option></select></label><label>Search<input id="offshoreSearch" type="search" placeholder="PSV, AHTS, rigs, region…"></label><label class="sw-offshore-toggle"><input type="checkbox" id="offshoreCompare" checked> Compare same class with Q2</label></div>'+
 '<div class="sw-offshore-scroll" id="offshoreScroll" role="region" aria-label="Reported offshore vessel rates" tabindex="0" hidden><table class="sw-offshore-table"><thead><tr><th scope="col">Vessel / region</th><th scope="col">Issuer & source</th><th scope="col">Reported rate</th><th scope="col">Q2 comparison</th></tr></thead><tbody id="offshoreBody"></tbody></table></div>'+
 '<p class="sw-offshore-note" id="offshoreCount" role="status"></p>'+
 '<nav class="sw-offshore-links" aria-label="Shipping sections"><a href="#shippingBenchmarkAnchor">Freight route definitions ↓</a><a href="#voyageEstimator">Voyage calculator ↓</a><a href="health.html">Data health ↗</a></nav>'+
 '<details class="sw-offshore-explain"><summary>What these dayrates mean — and what is not available yet</summary><div><p>These are reported averages over Q2/Q3 2026 company operating periods. Vessel revenue per day worked and rig revenue per operating day are not identical rate definitions. A regional fleet average does not price any vessel available for hire today.</p><p><strong>Licensed daily PSV, AHTS and freight spot quotes: 0.</strong> Broker reports and Baltic, Braemar and Clarksons benchmark bars cannot be published as a live quote service without an appropriate licence. We retain the existing route definitions, fuel/voyage model and official transport indices below, separately labelled.</p><p>All quarterly rate rows link to original issuer/SEC evidence. No raw licensed broker benchmark is stored in this dataset; historical rates are not inferred from listed stock prices.</p></div></details>';
 return n;
}
function render(node,d,src){
 const last=d.observations.map(r=>r.period).sort().at(-1);
 const latest=d.observations.filter(r=>r.period===last);
 const history=new Map(d.observations.map(r=>[[r.sourceId,r.vesselClass,r.region,r.period].join('|'),r]));
 node.querySelector('#offshoreStatus').innerHTML='<strong>'+latest.length+' published '+H(Q(last))+' class averages</strong><span>'+src.size+' original source reports · '+d.observations.length+' source-dated facts · <strong>0 licensed daily spot quotes</strong></span>';
 const chosen=[
 latest.find(r=>r.sourceId==='tdw2026q3'&&r.vesselClass==='PSV >900 m²'),
 latest.find(r=>r.sourceId==='tdw2026q3'&&r.vesselClass==='AHTS >16K BHP'),
 latest.find(r=>r.sourceId==='smhi2026q3'&&r.vesselClass==='PSV fleet'),
 latest.find(r=>r.sourceId==='noble2026q3'&&r.vesselClass==='Floating rigs')
 ].filter(Boolean);
 node.querySelector('#offshoreHighlights').innerHTML=chosen.map(r=>'<article class="sw-offshore-card"><small>'+H(r.segment)+' · '+H(r.region)+'</small><strong>'+H(USD.format(r.value))+'<span> / day</span></strong><span>'+H(r.vesselClass)+'</span><small>'+H(src.get(r.sourceId).issuer)+' · '+H(Q(r.period))+'</small></article>').join('');
 const seg=node.querySelector('#offshoreSegment'),issuer=node.querySelector('#offshoreIssuer'),search=node.querySelector('#offshoreSearch'),compare=node.querySelector('#offshoreCompare');
 for(const x of [...new Set(latest.map(r=>r.segment))].sort()){const opt=document.createElement('option');opt.value=x;opt.textContent=x;seg.appendChild(opt)}
 for(const s of src.values()){const opt=document.createElement('option');opt.value=s.id;opt.textContent=s.issuer;issuer.appendChild(opt)}
 function update(){
  const q=search.value.toLowerCase().trim();
  const rows=latest.filter(r=>(seg.value==='all'||seg.value===r.segment)&&(issuer.value==='all'||issuer.value===r.sourceId)&&(!q||[r.segment,r.vesselClass,r.region,src.get(r.sourceId).issuer].join(' ').toLowerCase().includes(q)));
  rows.sort((a,b)=>a.segment.localeCompare(b.segment)||a.vesselClass.localeCompare(b.vesselClass));
  node.querySelector('#offshoreBody').innerHTML=rows.map(r=>{
   const s=src.get(r.sourceId),previous=history.get([r.sourceId,r.vesselClass,r.region,'2026-Q2'].join('|'));
   const change=compare.checked&&previous?'<strong class="sw-offshore-change">'+H(PCT.format((r.value/previous.value-1)*100))+'%</strong><small>vs '+H(USD.format(previous.value))+' in Q2</small>':'<span class="sw-offshore-muted">—</span>';
   const sourceUrl=/^https:\/\/[^\s"]+$/.test(s.url)?s.url:'';
   return '<tr><td><strong>'+H(r.vesselClass)+'</strong><small>'+H(r.segment)+' · '+H(r.region)+'</small></td>'+
    '<td><strong>'+H(s.issuer)+'</strong><small>'+H(Q(r.period))+' · filed '+H(s.published)+'</small><a href="'+H(sourceUrl)+'" target="_blank" rel="noopener noreferrer">Original source ↗</a></td>'+
    '<td><strong class="sw-offshore-value">'+H(USD.format(r.value))+'</strong><small>'+H(r.unit)+' · '+H(r.rateBasis)+'</small></td><td>'+change+'</td></tr>';
  }).join('')||'<tr><td colspan="4">No company-reported rates match these filters. Try another class or issuer.</td></tr>';
  node.querySelector('#offshoreCount').textContent=rows.length+' of '+latest.length+' historical company rate observations · '+Q(last)+' · not a live spot charter board.';
 }
 [seg,issuer,compare].forEach(x=>x.addEventListener('change',update));search.addEventListener('input',update);
 node.querySelector('#offshoreControls').hidden=false;
 node.querySelector('#offshoreScroll').hidden=false;
 update();
}
function mount(){
 if(document.getElementById('offshoreRates'))return;
 const top=host.querySelector('.sw-hero'),route=host.querySelector('#shippingBenchmarkAnchor');
 if(!top||!route)return;
 // Real published rates are the primary market task, before old route catalog widgets.
 const n=create();top.insertAdjacentElement('beforebegin',n);
 load().then(({d,src})=>{if(document.getElementById('offshoreRates')===n)render(n,d,src)}).catch(()=>{
  if(document.getElementById('offshoreRates')===n){n.querySelector('#offshoreStatus').textContent='Original offshore rate evidence is temporarily unavailable. Existing shipping data and routes remain below.';n.classList.add('sw-offshore-error')}
 });
}
function schedule(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;mount()})}
const observer=new MutationObserver(schedule);observer.observe(host,{childList:true,subtree:true});schedule();
window.addEventListener('pagehide',()=>observer.disconnect(),{once:true});
})();