/* V105: report only. Do not modify any market price, heatmap or quote source. */
(function(){
'use strict';
const root=document.getElementById('dailyPriceCoverage');
if(!root)return;
const text=(tag,value,cls)=>{
 const node=document.createElement(tag);
 if(cls)node.className=cls;
 node.textContent=String(value);
 return node;
};
const append=(parent,...nodes)=>nodes.forEach(n=>parent.append(n));
const integer=x=>Number.isInteger(x)&&x>=0?x.toLocaleString('en-GB'):'Not measured';
function card(label,number,note){
 const item=text('div','','sw105-stat');
 append(item,text('small',label),text('strong',integer(number)),text('span',note,'sw-meta'));
 return item;
}
function render(data){
 if(!data||data.schemaVersion!==1||!data.summary||!Array.isArray(data.byVenue))throw Error('Invalid coverage report');
 const s=data.summary;
 if(!Number.isInteger(s.listings)||s.listings<1||s.datedPrice+s.missingPrice!==s.listings)
  throw Error('Incomplete coverage accounting');
 root.replaceChildren();
 const status=text('p','Comparison date '+(data.comparisonDate||'unavailable')+' · weekday UTC estimate, not a venue-specific official close.','sw-meta');
 const grid=text('div','','sw105-summary');
 append(grid,
  card('Research listings',s.listings,'Target: every exchange trading session'),
  card('Dated prices',s.datedPrice,'Last-known observations'),
  card('Dated on comparison day',s.targetDatedPrice,'Not independently exchange-certified'),
  card('Monitored session comparable',s.monitoredComparableHeuristic,'Heuristic only; see source status'),
  card('Still without a price',s.missingPrice,'Requires a suitable quote source'),
  card('Licensed historical charts',s.licensedHistory,'Real stored bars only'));
 const note=text('p','Existing hourly/frequent sources, heatmap and graphs are preserved. A/B pair references ('+integer(s.pairOnly)+') are not complete daily series. Official EOD verification remains separate.','sw-meta');
 const controls=text('div','','sw105-venue-head');
 append(controls,text('h3','Daily coverage by exchange'));
 const link=document.createElement('a');
 link.href='data/daily-price-recovery-v105.json';link.className='sw-textlink';
 link.textContent='Inspect price and identity recovery queue';
 controls.append(link);
 const wrap=text('div','','sw105-table-wrap');
 const table=document.createElement('table');
 table.className='sw105-table';
 const header=document.createElement('thead'), hr=document.createElement('tr');
 for(const label of ['Exchange','Listings','Dated price','Target date','Missing','Exact ID'])append(hr,text('th',label));
 header.append(hr);
 const body=document.createElement('tbody');
 for(const v of data.byVenue){
  if(!v||typeof v.venue!=='string'||!Number.isInteger(v.listings))continue;
  const tr=document.createElement('tr');
  append(tr,text('th',v.venue),text('td',integer(v.listings)),
   text('td',integer(v.datedPrice)),text('td',integer(v.targetDatedPrice)),
   text('td',integer(v.missingPrice)),text('td',integer(v.exactIdentity)));
  body.append(tr);
 }
 append(table,header,body);wrap.append(table);
 const caveat=text('p',data.notice||'Source and licensing verification required.','sw-meta');
 append(root,status,grid,note,controls,wrap,caveat);
}
fetch('data/daily-price-coverage-v105.json',{cache:'no-store'})
 .then(r=>{if(!r.ok)throw Error('Coverage audit not published');return r.json();})
 .then(render)
 .catch(()=>{root.replaceChildren(text('p','The 500-listing daily coverage audit is not available yet. Existing scanner and market views continue unchanged.','sw-meta'));});
})();
