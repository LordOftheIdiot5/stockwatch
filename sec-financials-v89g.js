/* SEC issuer financial history: exact CIK, reported unit and duration; no derived quarters. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.StockwatchSECFinancials=api})(typeof window!=='undefined'?window:globalThis,function(){
'use strict';
const tags={RevenueFromContractWithCustomerExcludingAssessedTax:'Revenue from customer contracts',Revenues:'Revenue',SalesRevenueNet:'Net sales',NetIncomeLoss:'Net income',OperatingIncomeLoss:'Operating income',Assets:'Total assets',Liabilities:'Total liabilities',StockholdersEquity:'Shareholders’ equity',CashAndCashEquivalentsAtCarryingValue:'Cash and cash equivalents',NetCashProvidedByUsedInOperatingActivities:'Operating cash flow',PaymentsToAcquirePropertyPlantAndEquipment:'Capital expenditure',EarningsPerShareDiluted:'Diluted EPS',CommonStockSharesOutstanding:'Common shares outstanding',LongTermDebtCurrent:'Current long-term debt',LongTermDebtNoncurrent:'Noncurrent long-term debt'};
const isDay=s=>typeof s==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(s)&&Number.isFinite(Date.parse(s))&&new Date(Date.parse(s)).toISOString().slice(0,10)===s;
function unit(tag){return tag==='EarningsPerShareDiluted'?'USD/shares':tag==='CommonStockSharesOutstanding'?'shares':'USD'}
function duration(r){if(!r.start)return 'instant';const n=(Date.parse(r.end)-Date.parse(r.start))/86400000+1;return n>=330&&n<=380?'annual':n>=75&&n<=105?'quarter':'other'}
function rows(payload,cik){
 if(!/^\d{10}$/.test(cik)||payload?.cik!==cik||payload.taxonomy!=='us-gaap')throw Error('Issuer identity mismatch');
 return Object.values(payload.records||{}).filter(r=>{
 if(!r||!Object.hasOwn(tags,r.tag)||r.unit!==unit(r.tag)||!Number.isFinite(r.value)||!isDay(r.end)||!isDay(r.filed)||r.end>r.filed||(r.start&&(!isDay(r.start)||r.start>r.end))||!/^\d{10}-\d{2}-\d{6}$/.test(r.accession)||!['10-K','10-Q','20-F','40-F','10-K/A','10-Q/A','20-F/A','40-F/A'].includes(r.form))return false;
 const expected='https://www.sec.gov/Archives/edgar/data/'+Number(cik)+'/'+r.accession.replaceAll('-','')+'/'+r.accession+'-index.htm';return r.sourceUrl===expected;
 }).sort((a,b)=>b.end.localeCompare(a.end)||b.filed.localeCompare(a.filed)||b.accession.localeCompare(a.accession));
}
function select(records,tag,period){return records.filter(r=>r.tag===tag&&(period==='all'||duration(r)===period))}
function mount(host,row,load){
 const make=(tag,text,cls)=>{const e=document.createElement(tag);if(text!=null)e.textContent=text;if(cls)e.className=cls;return e};
 const head=make('h2','Financial statements');const state=make('p','Loading SEC as-filed observations…','sw-meta');state.setAttribute('role','status');host.replaceChildren(head,state);
 if(!/^\d{10}$/.test(row.cik)){state.textContent='Issuer identifier unavailable.';return}
 Promise.resolve().then(()=>load('data/sec-companyfacts/index.json')).then(idx=>{
 const e=idx?.issuers?.[row.cik];if(!e||!e.listingIds?.includes(row.id)||e.path!=='data/sec-companyfacts/'+row.cik+'.json')throw Error('No matching financial inventory');
 return load(e.path).then(data=>({data,e}));
 }).then(({data,e})=>{
 if(!host.isConnected)return;const records=rows(data,row.cik);
 if(!records.length)throw Error('No validated observations');
 state.textContent=records.length.toLocaleString()+' as-filed observations · last successful collection '+String(e.lastSuccess||'unknown')+(e.status==='ok'?'':' · retained data; refresh status '+e.status);
 const note=make('p','Reported values, not normalized financial ratios. Different reporting periods and filing revisions remain separate. Quarterly duration excludes year-to-date figures.','sw-meta');
 const controls=make('div',null,'sw-controls'),metric=make('select'),period=make('select');metric.setAttribute('aria-label','Financial metric');period.setAttribute('aria-label','Reporting period');
 function opt(el,value,label){const o=make('option',label);o.value=value;el.append(o)}
 for(const [k,v] of Object.entries(tags))if(records.some(r=>r.tag===k))opt(metric,k,v);
 for(const [k,v] of [['annual','Annual duration'],['quarter','Standalone quarter duration'],['instant','Balance-sheet / point-in-time'],['other','Other durations'],['all','All reported periods']])opt(period,k,v);
 period.value=records.some(r=>r.tag===metric.value&&duration(r)==='annual')?'annual':'all';
 controls.append(metric,period);const table=make('div',null,'sw-tablewrap'),count=make('p',null,'sw-meta'),more=make('button','Show more','sw-soft-btn');more.type='button';let limit=12;
 function draw(){const list=select(records,metric.value,period.value);count.textContent=list.length+' as-filed observations · '+unit(metric.value)+' · newest period first';more.hidden=list.length<=limit;table.replaceChildren();
 if(!list.length){table.append(make('p','No observations for this reporting duration. Select another period.','sw-note'));return}
 const t=make('table',null,'sw-table'),thead=make('thead'),tr=make('tr');for(const label of ['Period','Reported value','Filed','Filing'])tr.append(make('th',label));thead.append(tr);const tbody=make('tbody');
 for(const r of list.slice(0,limit)){const rr=make('tr');rr.append(make('td',r.start?r.start+' – '+r.end:r.end),make('td',new Intl.NumberFormat('en-US',{maximumFractionDigits:6}).format(r.value)+' '+r.unit),make('td',r.filed));const cell=make('td'),a=make('a',r.form+' ↗','sw-textlink');a.href=r.sourceUrl;a.target='_blank';a.rel='noopener noreferrer';cell.append(a);rr.append(cell);tbody.append(rr)}
 t.append(thead,tbody);table.append(t)}
 metric.addEventListener('change',()=>{limit=12;if(!select(records,metric.value,period.value).length)period.value='all';draw()});period.addEventListener('change',()=>{limit=12;draw()});more.addEventListener('click',()=>{limit+=24;draw()});host.append(note,controls,count,table,more);draw();
 }).catch(()=>{if(host.isConnected)state.textContent='Financial observations are not available from the published archive right now. Use the original SEC filings link above.'});
}
return {rows,select,duration,mount};
});
