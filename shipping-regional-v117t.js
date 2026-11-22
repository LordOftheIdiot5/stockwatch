/* Stockwatch S2 — already archived Eurostat + World Bank shipping activity.
 * Not charter/ship spot rates, not vessel-specific AIS tracks. */
(() => {
'use strict';
if(document.body.dataset.page!=='shipping')return;
const root=document.getElementById('v4app');if(!root)return;
const H=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const nfmt=new Intl.NumberFormat('en-US',{maximumFractionDigits:1});
const num=x=>nfmt.format(x);
const million=x=>nfmt.format(x/1000)+'m';
const countries=['NO','SE','DK','NL','DE','EU27_2020'];
const src='https://ec.europa.eu/eurostat/databrowser/view/mar_go_qmc/default/table?lang=en';
let load=null;
function validate(r,p){
 if(r.schemaVersion!==1||r.provider!=='Eurostat'||r.datasetCode!=='mar_go_qmc'||!Array.isArray(r.series)||!r.observedOn)throw Error('Eurostat source unavailable');
 if(!Array.isArray(p.series)||!p.source||p.source.sourceUrl!=='https://data.worldbank.org/indicator/IS.SHP.GOOD.TU')throw Error('World Bank port activity unavailable');
 const byCountry=new Map();
 for(const item of r.series){
  if(!countries.includes(item.countryCode)||item.unit!=='thousand tonnes'||item.frequency!=='quarterly'||item.key!=='eurostat:mar_go_qmc:RO_TOT:'+item.countryCode||!Array.isArray(item.history))continue;
  const sorted=item.history.filter(v=>/^\d{4}-Q[1-4]$/.test(v.period)&&Number.isFinite(v.value)&&v.value>=0).sort((a,b)=>a.period.localeCompare(b.period));
  if(sorted.length)byCountry.set(item.countryCode,{...item,history:sorted,period:sorted.at(-1).period,value:sorted.at(-1).value});
 }
 const nor=p.series.find(v=>v.countryCode==='NOR'&&v.unit==='TEU'&&v.frequency==='annual'&&/^\d{4}$/.test(v.period)&&Number.isFinite(v.value)&&v.value>0);
 if(!byCountry.has('NO')||!byCountry.has('SE')||!byCountry.has('EU27_2020')||!nor)throw Error('Missing Norwegian / European data');
 return {r,p,byCountry,nor};
}
function make(){
 const s=document.createElement('section');s.id='nordicMaritime';s.className='sw-panel sw-nordic';s.setAttribute('aria-labelledby','nordicMaritimeTitle');
 s.innerHTML='<div class="sw-nordic-hd"><div><span class="sw-kicker">NORWAY & EUROPE / PRIMARY-SOURCE DATA</span><h2 id="nordicMaritimeTitle">Nordic and European shipping pulse</h2><p>Actual published Ro-Ro cargo weight and container-port throughput. Each country has its own reporting period; these figures are <strong>not</strong> charter rates, AIS positions or shipping-company revenue.</p></div><a href="#roroMarketTraffic">Historical Ro-Ro charts ↓</a></div>'+
 '<p class="sw-nordic-status" id="nordicStatus" role="status">Loading saved official maritime data…</p>'+
 '<div id="nordicCards" class="sw-nordic-cards"></div>'+
 '<div class="sw-nordic-actions"><a href="https://kystdatahuset.kystverket.no/ws/swagger/index.html" target="_blank" rel="noopener noreferrer">Kystverket coastal data API ↗</a><a href="https://www.ssb.no/en/statbank1/table/09518/" target="_blank" rel="noopener noreferrer">SSB Norwegian port calls ↗</a><a href="https://www.ssb.no/en/statbank1/table/08923/" target="_blank" rel="noopener noreferrer">SSB maritime goods ↗</a><a href="'+src+'" target="_blank" rel="noopener noreferrer">Eurostat original dataset ↗</a></div>'+
 '<details class="sw-nordic-details"><summary>Compare latest available European quarters</summary><div class="sw-nordic-table-wrap" role="region" aria-label="Eurostat reported Ro-Ro volumes by country" tabindex="0"><table class="sw-nordic-table"><thead><tr><th>Region</th><th>Latest reported quarter</th><th>Ro-Ro cargo, thousand tonnes</th><th>Same-quarter annual change</th></tr></thead><tbody id="nordicRows"></tbody></table></div></details>'+
 '<p class="sw-nordic-foot">Eurostat \`mar_go_qmc\`: Ro-Ro mobile self-propelled and non-self-propelled cargo at main ports, in thousand tonnes. World Bank/UNCTAD container traffic: annual TEU including empty and transshipment containers. These are different measurements. EU-27 overlaps member-country totals; never sum it with the countries.</p>';
 return s;
}
function render(node,d){
 const {r,p,byCountry,nor}=d;
 const card=(title,value,metric,period)=>'<article class="sw-nordic-card"><small>'+H(title)+'</small><strong>'+H(value)+'</strong><span>'+H(metric)+'</span><small>'+H(period)+'</small></article>';
 const no=byCountry.get('NO'),se=byCountry.get('SE'),eu=byCountry.get('EU27_2020');
 node.querySelector('#nordicStatus').textContent='Eurostat archive checked '+r.observedOn+' · World Bank port activity source '+(p.source.status==='ok'?'connected':'last-known dated snapshot')+'.';
 node.querySelector('#nordicCards').innerHTML=card('Norway · Ro-Ro cargo',million(no.value),'million tonnes',no.period)+
  card('Sweden · Ro-Ro cargo',million(se.value),'million tonnes',se.period)+
  card('EU-27 · Ro-Ro cargo',million(eu.value),'million tonnes',eu.period)+
  card('Norway · container throughput',num(nor.value),'TEU / year',nor.period);
 const ordered=countries.map(k=>byCountry.get(k)).filter(Boolean);
 node.querySelector('#nordicRows').innerHTML=ordered.map(x=>{
  const previous=x.history.find(z=>z.period===String(Number(x.period.slice(0,4))-1)+x.period.slice(4));
  const delta=previous&&previous.value>0?(100*(x.value/previous.value-1)):null;
  const shown=delta===null?'Not published':(delta>=0?'+':'')+new Intl.NumberFormat('en-US',{maximumFractionDigits:1}).format(delta)+'%';
  return '<tr><td><strong>'+H(x.label)+'</strong></td><td>'+H(x.period)+'</td><td>'+H(num(x.value))+'</td><td>'+H(shown)+'</td></tr>';
 }).join('');
}
function mount(){
 if(root.querySelector('#nordicMaritime'))return;
 const anchor=root.querySelector('#shippingWorldMap')||root.querySelector('#usdaRouteRates');if(!anchor)return;
 const node=make();anchor.insertAdjacentElement('afterend',node);
 if(!load)load=Promise.all([
  fetch('data/shipping-roro-traffic.json',{cache:'no-store'}).then(x=>{if(!x.ok)throw Error('roro');return x.json()}),
  fetch('data/shipping-ports.json',{cache:'no-store'}).then(x=>{if(!x.ok)throw Error('ports');return x.json()})
 ]).then(([r,p])=>validate(r,p));
 load.then(d=>{if(root.querySelector('#nordicMaritime')===node)render(node,d)}).catch(()=>{
  if(root.querySelector('#nordicMaritime')===node)node.querySelector('#nordicStatus').textContent='Norwegian and European source data temporarily unavailable. Existing dated Ro-Ro history and original SSB/Kystverket links remain below.';
 });
}
let queued=false;
const mo=new MutationObserver(()=>{if(!queued){queued=true;requestAnimationFrame(()=>{queued=false;mount()})}});
mo.observe(root,{childList:true,subtree:true});mount();
window.addEventListener('pagehide',()=>mo.disconnect(),{once:true});
})();