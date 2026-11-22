/* Stockwatch S2 — original NavProfit concept, rights-safe OSV contract scenarios.
 * Financial projection only. Never infer a broker spot rate, live bunker price,
 * navigable sea distance, accounting profit or real charter contract.
 * No accounts, tokens, AIS keys or private vessel data are accessed. */
(function(global){
'use strict';
function compute(x){
 const keys=['rate','serviceDays','billableDays','transitDays','fuelTonnesPerDay','bunkerUsdPerTonne',
  'dailyOpex','portCosts','otherCosts','commissionPct','contingencyPct'];
 if(!x||keys.some(k=>typeof x[k]!=='number'||!Number.isFinite(x[k])||x[k]<0))return null;
 if(!(x.rate>0&&x.serviceDays>0&&x.billableDays>0&&x.billableDays<=x.serviceDays&&
  x.commissionPct<100&&x.contingencyPct<=100&&x.bunkerUsdPerTonne<=50000))return null;
 const totalDays=x.serviceDays+x.transitDays;
 const gross=x.rate*x.billableDays;
 const commission=gross*x.commissionPct/100;
 const fuelTonnes=x.fuelTonnesPerDay*totalDays;
 const bunkerCost=fuelTonnes*x.bunkerUsdPerTonne;
 const operatingCost=x.dailyOpex*totalDays;
 const otherCosts=x.portCosts+x.otherCosts;
 const baseCost=bunkerCost+operatingCost+otherCosts;
 const contingencyCost=baseCost*x.contingencyPct/100;
 const nonCommissionCost=baseCost+contingencyCost;
 const contribution=gross-commission-nonCommissionCost;
 const breakEvenDayrate=nonCommissionCost/(x.billableDays*(1-x.commissionPct/100));
 const out={totalDays,gross,commission,fuelTonnes,bunkerCost,operatingCost,otherCosts,contingencyCost,nonCommissionCost,contribution,breakEvenDayrate,contributionMarginPct:100*contribution/gross};
 return Object.values(out).every(Number.isFinite)?out:null;
}
global.StockwatchOSVEconomics={compute};
if(!global.document||global.document.body?.dataset.page!=='shipping')return;
const root=global.document.getElementById('v4app');if(!root)return;
const money=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:0});
const H=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fields=[
 ['serviceDays','Service days (calendar)',30,1,365],
 ['billableDays','Billable operating days',25,1,365],
 ['transitDays','Unpaid transit days',3,0,100],
 ['dailyOpex','Assumed vessel OPEX (USD/day)',12000,0,200000],
 ['fuelTonnesPerDay','Assumed daily fuel burn (tonnes)',5,0,200],
 ['bunkerUsdPerTonne','Assumed bunker cost (USD/tonne)',600,0,50000],
 ['portCosts','Port and mobilization fees (USD total)',20000,0,50000000],
 ['otherCosts','Other charter costs (USD total)',0,0,50000000],
 ['commissionPct','Brokerage and commission (%)',2,0,99],
 ['contingencyPct','Expense contingency (%)',5,0,100]
];
let sourcePromise=null;
function create(){
 const n=global.document.createElement('section');
 n.id='navprofitEconomics';n.className='sw-panel sw-osv-econ';n.setAttribute('aria-labelledby','osvEconTitle');
 n.innerHTML='<span class="sw-kicker">NAVPROFIT → STOCKWATCH / VOYAGE RESEARCH</span><h2 id="osvEconTitle">Offshore charter economics</h2>'+
 '<p>A research calculator adapted from <a href="https://github.com/LordOftheIdiot5/navprofit" target="_blank" rel="noopener noreferrer">NavProfit</a>\'s voyage-profit approach. Enter your assumptions to calculate gross revenue, operating costs, contribution and break-even rate. Historical reported issuer dayrates are a starting point, <strong>not a current charter offer or an actual company margin</strong>.</p>'+
 '<details class="sw-osv-details"><summary>Model a vessel charter from a source-reported rate</summary>'+
 '<form id="osvEconForm"><div class="sw-osv-controls"><label for="osvEconBasis">Original reported-rate basis<select id="osvEconBasis" required><option value="">Loading company-rate observations…</option></select></label>'+
 '<label for="osvEconRate">Scenario dayrate (USD/day)<input id="osvEconRate" type="number" min="1" max="2000000" step="1" required></label></div>'+
 '<p class="sw-osv-citation" id="osvEconCitation">Rates will be sourced from original issuer reports.</p><div class="sw-osv-fields" id="osvEconFields"></div>'+
 '<button type="submit" class="sw-osv-run">Calculate illustrative operating contribution</button><div id="osvEconResults" role="status" aria-live="polite"></div></form></details>'+
 '<p class="sw-osv-disclaimer">Model assumptions are hypothetical, including bunker costs and vessel OPEX. No automatically imported NavProfit demonstration port distances/prices, AIS positions, invoices, accounts or API keys. Calculated operating contribution excludes capital cost, taxes, finance, depreciation and corporate overhead.</p>';
 return n;
}
function mount(){
 if(root.querySelector('#navprofitEconomics'))return;
 const regional=root.querySelector('#nordicMaritime');if(!regional)return;
 const node=create();regional.insertAdjacentElement('afterend',node);
 const inputs=node.querySelector('#osvEconFields');
 inputs.innerHTML=fields.map(([key,label,value,min,max])=>'<label for="osv_'+key+'">'+H(label)+'<input id="osv_'+key+'" name="'+H(key)+'" type="number" step="any" min="'+min+'" max="'+max+'" value="'+value+'" required></label>').join('');
 if(!sourcePromise)sourcePromise=fetch('data/offshore-rate-evidence-v117s.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('missing reported rate');return r.json()}).then(d=>{
   if(d.schemaVersion!==1||!Array.isArray(d.observations)||!Array.isArray(d.sources)||d.brokerSpotRatesLicensed!==0)throw Error('invalid report basis');
   const sources=new Map(d.sources.map(x=>[x.id,x]));
   return d.observations.filter(x=>x.period==='2026-Q3'&&x.rateType==='issuer_reported_quarterly_average'&&x.unit==='USD/day'&&x.isBrokerSpotQuote===false&&Number.isFinite(x.value)&&x.value>0&&sources.has(x.sourceId)).map(x=>({...x,source:sources.get(x.sourceId)}));
 });
 sourcePromise.then(rows=>{
  if(root.querySelector('#navprofitEconomics')!==node)return;
  if(!rows.length)throw Error('no original issuer observations');
  const select=node.querySelector('#osvEconBasis'), rate=node.querySelector('#osvEconRate'),citation=node.querySelector('#osvEconCitation'),result=node.querySelector('#osvEconResults');
  select.replaceChildren();
  for(const r of rows){const opt=global.document.createElement('option');opt.value=r.id;opt.textContent=r.source.issuer+' — '+r.vesselClass+' ('+r.region+', '+r.period+')';select.append(opt)}
  function sync(){
   const source=rows.find(x=>x.id===select.value)||rows[0];
   rate.value=String(source.value);result.replaceChildren();
   citation.innerHTML='Base: <strong>'+H(source.source.issuer)+' / '+H(source.vesselClass)+' / '+H(source.region)+'</strong> · '+H(source.period)+' issuer-reported average ('+H(money.format(source.value))+'/day). <a href="'+H(source.source.url)+'" target="_blank" rel="noopener noreferrer">Original disclosure ↗</a>. All costs below are user-editable illustrative assumptions.';
  }
  select.addEventListener('change',sync);sync();
  node.querySelector('#osvEconForm').addEventListener('submit',event=>{
   event.preventDefault();const source=rows.find(x=>x.id===select.value)||rows[0];
   const v={rate:Number(rate.value)};
   for(const [key] of fields)v[key]=Number(node.querySelector('#osv_'+key).value);
   const res=compute(v);
   if(!res){result.textContent='Check all assumptions: billable days must be positive and cannot exceed service days; rate and days must be finite positive numbers.';return}
   const metrics=[
    ['Illustrative gross revenue',money.format(res.gross)],
    ['Fuel cost',money.format(res.bunkerCost)],
    ['Vessel operating cost',money.format(res.operatingCost)],
    ['Commission + other + contingency',money.format(res.commission+res.otherCosts+res.contingencyCost)],
    ['Illustrative operating contribution',money.format(res.contribution)],
    ['Break-even dayrate',money.format(res.breakEvenDayrate)]
   ];
   result.innerHTML='<div class="sw-osv-results">'+metrics.map(([label,val])=>'<div><small>'+H(label)+'</small><strong>'+H(val)+'</strong></div>').join('')+'</div>'+
    '<p class="sw-osv-citation">Scenario based on user inputs and the <a href="'+H(source.source.url)+'" target="_blank" rel="noopener noreferrer">'+H(source.source.issuer)+' '+H(source.period)+' published average</a>. This is <strong>not</strong> a reported margin, booking offer or live vessel charter rate.</p>';
  });
 }).catch(()=>{if(root.querySelector('#navprofitEconomics')===node)node.querySelector('#osvEconCitation').textContent='Original company rate data unavailable. Scenario cannot load; the independent regional and freight datasets remain available.'});
}
let queued=false;const observer=new MutationObserver(()=>{if(!queued){queued=true;requestAnimationFrame(()=>{queued=false;mount()})}});
observer.observe(root,{childList:true,subtree:true});mount();
global.addEventListener('pagehide',()=>observer.disconnect(),{once:true});
})(typeof window!=='undefined'?window:globalThis);
