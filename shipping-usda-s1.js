/* Shipping S1b — USDA weekly bulk-grain route freight, USD/metric tonne.
 * Do not combine these costs with issuer USD/day OSV/rig operating averages. */
(() => {
 'use strict';
 if(document.body.dataset.page!=='shipping')return;
 const host=document.getElementById('v4app');if(!host)return;
 const H=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let fetched=null;
 function create(){
  const s=document.createElement('section');
  s.id='usdaRouteRates';s.className='sw-panel sw-usda-rates';
  s.setAttribute('aria-labelledby','usdaRateTitle');
  s.innerHTML='<header><div><span class="sw-kicker">OFFICIAL PUBLIC FREIGHT PRICES</span><h2 id="usdaRateTitle">Bulk-grain ocean routes</h2><p>USDA-reported freight costs per metric tonne — <strong>not</strong> offshore vessel USD/day charter rates, Baltic spot indexes or container rates.</p></div></header>'+
    '<div id="usdaRateStatus" role="status" class="sw-usda-status">Loading original USDA report figures…</div>'+
    '<div id="usdaRateCards" class="sw-usda-grid"></div>'+
    '<p class="sw-usda-note">These are published freight indications for U.S. grain exports to Japan, not executable transport quotations, and cannot be generalized to other cargoes or corridors. The USDA report has an inconsistent prior-week Gulf comparison, so no unsourced weekly percentage change is shown.</p>';
  return s;
 }
 function render(node,d){
  if(d.schemaVersion!==1||d.unit!=='USD/metric_ton'||d.isExecutableQuote!==false||d.isContainerRate!==false||!Array.isArray(d.rates)||d.rates.length!==2||!/^https:\/\/www\.ams\.usda\.gov\//.test(d.sourceUrl))throw Error('Invalid freight source');
  const format=v=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',minimumFractionDigits:2,maximumFractionDigits:2}).format(v);
  for(const r of d.rates)if(!r.id||!r.route||!Number.isFinite(r.value)||r.value<=0||r.unit!=='USD/metric_ton'||r.observationDate!==d.observationDate)throw Error('Unverified freight observation');
  node.querySelector('#usdaRateStatus').innerHTML='<strong>Reported '+H(d.observationDate)+'</strong><span>Published '+H(d.reportedAt)+' · '+H(d.source)+'</span>';
  node.querySelector('#usdaRateCards').innerHTML=d.rates.map(r=>'<article class="sw-usda-card"><small>'+H(r.cargo)+' · '+H(r.observationDate)+'</small><h3>'+H(r.route)+'</h3><strong>'+H(format(r.value))+'<span> / metric tonne</span></strong><a href="'+H(d.sourceUrl)+'" target="_blank" rel="noopener noreferrer">Original USDA report ↗</a></article>').join('');
 }
 function mount(){
  if(document.getElementById('usdaRouteRates'))return;
  const reference=document.getElementById('offshoreRates');
  if(!reference)return;
  const section=create();reference.insertAdjacentElement('afterend',section);
  if(!fetched)fetched=fetch('data/shipping-usda-ocean-rates-s1.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('HTTP '+r.status);return r.json()});
  fetched.then(d=>{if(document.getElementById('usdaRouteRates')===section)render(section,d)}).catch(()=>{
   if(document.getElementById('usdaRouteRates')===section)section.querySelector('#usdaRateStatus').textContent='USDA price snapshot unavailable; the remaining shipping research modules are unaffected.';
  });
 }
 let scheduled=false;
 const observer=new MutationObserver(()=>{if(!scheduled){scheduled=true;requestAnimationFrame(()=>{scheduled=false;mount()})}});
 observer.observe(host,{childList:true,subtree:true});
 mount();
 window.addEventListener('pagehide',()=>observer.disconnect(),{once:true});
})();