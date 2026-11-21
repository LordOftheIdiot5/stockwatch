/* V114: secondary-market task navigation over real, existing sections.
   Enhancement only: no source values, session dates or licensed price rights
   are fabricated or changed. */
(()=>{
 'use strict';
 const page=document.body.dataset.page;
 const cfg={
  spreads:[['spreadPairs','A/B pairs'],['abRanking','Relative-value watchlist'],
    ['spreadDetail','Selected pair']],
  shipping:[['shippingBenchmarkAnchor','Routes and classes'],
    ['routeCompare','Compare routes'],['voyageEstimator','Voyage scenario'],
    ['freightPPIContent','Official cost index'],['worldBankPortTraffic','Port activity']],
  commodities:[['commodityTabs','Market references']],
  shorts:[['shortsDisclosurePanel','Disclosed positions']],
  calendar:[['calendarUpcoming','Upcoming events'],['calendarDisclosures','Issuer filings']]
 };
 if(!Object.hasOwn(cfg,page))return;
 const app=document.getElementById(page==='calendar'?'app':'v4app');
 if(!app)return;
 const make=(tag,cls,content)=>{
  const n=document.createElement(tag);if(cls)n.className=cls;
  if(content!==undefined)n.textContent=content;
  return n;
 };
 let queued=false;
 function refresh(){
  const targets={
   abRanking:app.querySelector('.sw-ab-ranking'),
   shortsDisclosurePanel:app.querySelector('.sw-panel:has(.sw-tablewrap)'),
   calendarUpcoming:app.querySelector('.panel:has(#eventRows)'),
   calendarDisclosures:app.querySelector('.sw96-recent-filings')
  };
  for(const [id,node] of Object.entries(targets)){
   if(node&&!node.id)node.id=id;
  }
  const available=cfg[page].filter(([id])=>app.querySelector('#'+id));
  if(!available.length)return;
  let nav=app.querySelector(':scope > .sw114-tasknav');
  if(!nav){
   nav=make('nav','sw114-tasknav');
   nav.setAttribute('aria-label','On this research page');
   app.prepend(nav);
  }
  const signature=available.map(x=>x[0]).join('|');
  if(nav.dataset.sections===signature)return;
  nav.dataset.sections=signature;
  nav.replaceChildren();
  nav.append(make('strong','sw114-task-label','On this page'));
  const list=make('div','sw114-task-links');
  for(const [id,name] of available){
   const a=make('a','sw114-task-link',name);
   a.href='#'+id;list.append(a);
  }
  nav.append(list);
  const note=make('p','sw114-task-note',
    page==='shipping'?'Published benchmark descriptions, listed proxies and public indices are different measurements.':
    page==='spreads'?'Ratios require matched-session A/B observations. Older ratios are reference only.':
    page==='commodities'?'Dated last-known market references and listed proxies, not executable quotes.':
    page==='shorts'?'Register observations are dated disclosures, not complete live short interest.':
    'Future source-backed events and already published issuer filings are separate.');
  nav.append(note);
 }
 const observer=new MutationObserver(()=>{
  if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;refresh()});
 });
 observer.observe(app,{childList:true,subtree:true});
 refresh();
 window.addEventListener('pagehide',()=>observer.disconnect(),{once:true});
})();