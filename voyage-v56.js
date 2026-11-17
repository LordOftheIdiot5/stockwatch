/* User-entered scenario calculator, not a market-data source or navigation service. */
(function(global){'use strict';
const valid=x=>typeof x==='number'&&Number.isFinite(x)&&x>=0;
function compute(x){
 const fields=['ladenMiles','ballastMiles','speedLaden','speedBallast','portDays','cargoTonnes','freightPerTonne','commissionPct','fuelLaden','fuelBallast','fuelPort','fuelPrice','portCosts','otherVoyageCosts','dailyOpex'];
 if(!x||fields.some(k=>!valid(x[k]))||x.speedLaden<=0||x.speedBallast<=0||x.cargoTonnes<=0||x.commissionPct>100)return null;
 const laden=x.ladenMiles/(x.speedLaden*24),ballast=x.ballastMiles/(x.speedBallast*24),totalDays=laden+ballast+x.portDays;if(totalDays<=0)return null;
 const fuelTonnes=laden*x.fuelLaden+ballast*x.fuelBallast+x.portDays*x.fuelPort,gross=x.cargoTonnes*x.freightPerTonne,commission=gross*x.commissionPct/100,netRevenue=gross-commission,bunker=fuelTonnes*x.fuelPrice,voyageCosts=bunker+x.portCosts+x.otherVoyageCosts,tce=(netRevenue-voyageCosts)/totalDays,opex=x.dailyOpex*totalDays,margin=netRevenue-voyageCosts-opex;
 const denom=x.cargoTonnes*(1-x.commissionPct/100),breakEven=denom>0?(voyageCosts+opex)/denom:null;
 const out={laden,ballast,totalDays,fuelTonnes,gross,commission,netRevenue,bunker,voyageCosts,tce,opex,margin,breakEven};
 if(Object.values(out).some(v=>v!==null&&!Number.isFinite(v)))return null;
 return out;
}
const fields=[['ladenMiles','Laden sailing distance','nm'],['ballastMiles','Ballast / positioning distance','nm'],['speedLaden','Laden average speed','kn'],['speedBallast','Ballast average speed','kn'],['portDays','Total port and waiting days','days'],['cargoTonnes','Cargo quantity','tonnes'],['freightPerTonne','Assumed freight rate','USD/tonne'],['commissionPct','Freight commission','%'],['fuelLaden','Laden fuel consumption','tonnes/day'],['fuelBallast','Ballast fuel consumption','tonnes/day'],['fuelPort','Port fuel consumption','tonnes/day'],['fuelPrice','Assumed bunker price','USD/tonne'],['portCosts','Port, canal and agency costs','USD'],['otherVoyageCosts','Other voyage costs','USD'],['dailyOpex','Vessel operating costs','USD/day']];
const fmt=n=>n===null?'Unavailable':n.toLocaleString('en-GB',{maximumFractionDigits:2});
function mount(host){
 host.innerHTML='<section class="sw-panel sw56-voyage"><div class="sw-panel-hd"><div><h2>Voyage economics calculator</h2><small>Dry-bulk / weight-based voyage scenario · all monetary values USD</small></div></div><div class="sw-panel-pad"><p class="sw-meta">Enter your own assumptions. Nothing is prefilled with market data. This model covers USD/tonne voyage freight, not time-charter, Worldscale or container rates. Distances are supplied by you; not navigational guidance.</p><form><div class="sw56-inputs">'+fields.map(([k,n,u])=>'<label>'+n+' <small>'+u+'</small><input type="number" name="'+k+'" min="0" step="any" required'+(k==='commissionPct'?' max="100"':'')+' placeholder="Enter '+u+'"></label>').join('')+'</div><div class="sw-controls"><button class="sw-primary" type="submit">Calculate voyage</button><button class="sw-soft-btn" type="reset">Clear assumptions</button></div></form><div data-voyage-output role="status" aria-live="polite">Enter all assumptions to calculate a scenario.</div><p class="sw-meta">TCE = (freight revenue less commission and voyage costs) ÷ total voyage days. Operating costs are excluded from TCE and shown separately in operating contribution. No financing, depreciation, taxes, off-hire beyond entered days, cargo claims or capital return included. Not a quote or investment recommendation.</p></div></section>';
 const form=host.querySelector('form'),out=host.querySelector('[data-voyage-output]');
 form.addEventListener('submit',e=>{e.preventDefault();let v={};for(const [k] of fields){const f=form.elements.namedItem(k);if(!f.value.trim()){out.textContent='Complete every assumption, entering zero where appropriate.';return}v[k]=f.valueAsNumber}const r=compute(v);if(!r){out.textContent='Check the assumptions: cargo and speeds must be positive, voyage time nonzero, commission 0–100%.';return}
 out.innerHTML='<p class="sw-meta">User-entered scenario · not observed market data</p><div class="sw56-results">'+[['Total voyage duration',r.totalDays,'days'],['Fuel consumption',r.fuelTonnes,'tonnes'],['Gross freight revenue',r.gross,'USD'],['Net freight revenue',r.netRevenue,'USD'],['Voyage costs',r.voyageCosts,'USD'],['Time charter equivalent',r.tce,'USD/day'],['Vessel operating costs',r.opex,'USD'],['Operating contribution',r.margin,'USD'],['Operating break-even freight',r.breakEven,'USD/tonne']].map(([n,a,u])=>'<div><small>'+n+'</small><strong>'+fmt(a)+'</strong><span>'+u+'</span></div>').join('')+'</div>';
 });
 form.addEventListener('reset',()=>{out.textContent='Enter all assumptions to calculate a scenario.'});
 form.addEventListener('input',()=>{out.textContent='Assumptions changed. Recalculate to update the scenario.'});
}
const api={compute,mount};if(typeof module==='object'&&module.exports)module.exports=api;else global.StockwatchVoyage=api;
})(typeof window!=='undefined'?window:{});
