/* Source-linked company research presentation and period-safe financial calculations. */
(function(global){
'use strict';
const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const num=x=>typeof x==='number'&&Number.isFinite(x);
const dateOK=d=>typeof d==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d))&&new Date(d).toISOString().slice(0,10)===d;
function safe(u){try{let x=new URL(u);return x.protocol==='https:'&&x.hostname?x.href:''}catch{return ''}}
function financialSummary(f){
 if(!f||!dateOK(f.asOf)||!safe(f.sourceUrl)||!f.period||!f.currency)return null;
 const m=f.metrics||{},metrics={};for(const k of ['revenue','operatingIncome','adjustedOperatingIncome','netIncome','eps','dividendPerShare','marketCap','pe','pb','dividendYield'])if(num(m[k]))metrics[k]=m[k];
 const ratios=[];if(num(m.revenue)&&m.revenue>0){for(const [k,label] of [['operatingIncome','Reported operating margin'],['adjustedOperatingIncome','Adjusted operating margin'],['netIncome','Net margin']])if(num(m[k])){const value=m[k]/m.revenue*100;if(num(value))ratios.push({label,value})}}
 return {period:f.period,asOf:f.asOf,published:dateOK(f.published)?f.published:null,currency:f.currency,source:f.sourceName||'Issuer filing',sourceUrl:safe(f.sourceUrl),metrics,ratios};
}
const F=(n,d=2)=>num(n)?n.toLocaleString('en-GB',{maximumFractionDigits:d}):'Unavailable';
const labels={revenue:['Revenue','currency'],operatingIncome:['Reported operating income','currency'],adjustedOperatingIncome:['Adjusted operating income','currency'],netIncome:['Net income','currency'],eps:['Earnings per share','per share'],dividendPerShare:['Dividend per share','per share'],marketCap:['Market capitalization','currency'],pe:['P/E','multiple'],pb:['P/B','multiple'],dividendYield:['Dividend yield','percent']};
function financialHTML(f){const x=financialSummary(f);if(!x||!Object.keys(x.metrics).length)return '<h2>Financial statements</h2><p class="sw-note">No verified numeric statements for this listing yet. Missing earnings, valuation and dividend figures are not estimated.</p>';
 const row=(k,v)=>{const [label,type]=labels[k];let unit=type==='currency'?x.currency:type==='per share'?x.currency+'/share':type==='multiple'?'×':'%';return '<tr><th scope="row">'+E(label)+'</th><td>'+E(F(v,type==='currency'?0:4))+'</td><td>'+E(unit)+'</td></tr>'};
 return '<div class="sw-section-row"><h2>Financial statements</h2><a class="sw-textlink" target="_blank" rel="noopener noreferrer" href="'+E(x.sourceUrl)+'">Issuer filing ↗</a></div><div class="sw50-filing"><strong>'+E(x.period)+'</strong><span>Period end '+E(x.asOf)+' · '+E(x.currency)+' · Published '+E(x.published||'not recorded')+'</span><small>'+E(x.source)+'</small></div><div class="sw50-ratios">'+x.ratios.map(r=>'<div><small>'+E(r.label)+'</small><strong>'+E(F(r.value,2))+'%</strong></div>').join('')+'</div><div class="sw-tablewrap"><table class="sw-table sw50-statement"><thead><tr><th>Reported metric</th><th>Value</th><th>Unit</th></tr></thead><tbody>'+Object.entries(x.metrics).map(([k,v])=>row(k,v)).join('')+'</tbody></table></div><p class="sw-meta">Margins are calculated from figures in the same reported period. Adjusted and reported results stay separate; no annualization or missing values inferred.</p>';
}
function eventsFor(t,items){return (Array.isArray(items)?items:[]).filter(x=>x&&x.ticker===t&&dateOK(x.date)&&safe(x.sourceUrl)).sort((a,b)=>a.date.localeCompare(b.date))}
function actionHTML(t,items,issuer){
 const events=eventsFor(t,items),data=issuer?.ticker===t?issuer:null;
 const action=data?.previousTicker&&data.historyPolicy&&safe(data.corporateActionSource||data.evidence)?'<div class="sw50-filing"><strong>Listing identity change</strong><span>'+E(data.previousTicker)+' → '+E(t)+' · '+E(data.effectiveDate||'Effective date not recorded')+'</span><small>'+E(data.historyPolicy)+'</small><a class="sw-textlink" target="_blank" rel="noopener noreferrer" href="'+E(safe(data.corporateActionSource||data.evidence))+'">Identity evidence ↗</a></div>':'';
 return '<h2>Corporate events &amp; listing history</h2>'+action+(events.length?events.map(x=>'<div class="sw50-filing"><strong>'+E(x.title||x.event||x.type||'Corporate event')+'</strong><span>'+E(x.date)+' · '+E(x.type||'Event')+' · '+E(x.status||'Verify date with issuer')+'</span><a class="sw-textlink" target="_blank" rel="noopener noreferrer" href="'+E(safe(x.sourceUrl))+'">Source ↗</a></div>').join(''):'<p class="sw-note">No source-linked calendar events recorded for this ticker. This does not mean that no corporate actions have occurred.</p>')+'<p class="sw-meta">Historical identities are not automatically combined. Verify effective dates and adjustment conventions before comparing prices.</p>';
}
function coverageHTML({ticker,fundamental,issuer,figis,events,quality,date}){
 const f=financialSummary(fundamental),n=eventsFor(ticker,events).length;
 const row=(label,value,detail)=>'<div><small>'+E(label)+'</small><strong>'+E(value)+'</strong><span>'+E(detail)+'</span></div>';
 return '<div class="sw50-coverage" aria-label="Research coverage">'+row('Scanner observation',quality||'Unknown',date||'No date')+row('Issuer identity',issuer?.isin&&safe(issuer.evidence)?'Source-linked ISIN':'Reference only',issuer?.isin||'ISIN not established')+row('FIGI mappings',String(figis||0)+' candidates','Not independently verified')+row('Financial statement',f?f.period:'Not loaded',f?f.currency:'No estimates')+row('Calendar events',String(n),'Source-linked records only')+'</div>';
}
const api={financialSummary,eventsFor,financialHTML,actionHTML,coverageHTML};if(typeof module==='object'&&module.exports)module.exports=api;else global.StockwatchCompany=api;
})(typeof window!=='undefined'?window:{});
