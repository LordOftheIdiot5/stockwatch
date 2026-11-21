/* V113: preserve the selected, source-backed company when moving between tools.
 * Does not calculate a price, generate an event, or imply licensed history.
 */
(()=>{
 'use strict';
 if(document.body.dataset.page!=='company')return;
 const app=document.getElementById('v4app');
 if(!app)return;
 const sections=new Set(['chart','financials','filings','peers','events','drivers','identity']);
 const params=new URLSearchParams(location.search);
 const originalSection=params.get('section');
 const initialSection=sections.has(originalSection)?originalSection:
   (location.hash.startsWith('#sw94-company-')?
     location.hash.slice('#sw94-company-'.length):'');
 let first=true;
 function mount(){
  const panel=app.querySelector('.sw-company-research[data-sw110c-ready="true"]');
  const detail=app.querySelector('#stockDetail');
  if(!panel||!detail||panel.dataset.sw113Ready==='true')return false;
  const ticker=detail.dataset.currentTicker;
  const links=panel.querySelector('.sw-company-links');
  const tabs=panel.querySelector('.sw-company-tabs');
  if(!links||!tabs||!ticker||!/^[-A-Za-z0-9.]{1,40}$/.test(ticker))return false;
  panel.dataset.sw113Ready='true';
  const actions=[
    ['terminal.html?ticker='+encodeURIComponent(ticker),'Open in terminal'],
    ['compare.html?ticker='+encodeURIComponent(ticker),'Compare company'],
    ['intelligence.html?ticker='+encodeURIComponent(ticker),'Company connections'],
    ['news.html?q='+encodeURIComponent(ticker),'Issuer news'],
  ];
  for(const [href,label] of actions){
    if(links.querySelector('a[href="'+href+'"]'))continue;
    const a=document.createElement('a');
    a.className='sw-soft-btn sw113-research-action';
    a.href=href;a.textContent=label;
    a.setAttribute('data-sw113-action','true');
    links.append(a);
  }
  // Keep a shareable research section without routing people away from the
  // company or transforming the original evidence into new assertions.
  tabs.addEventListener('click',event=>{
    const button=event.target.closest('[data-company-tab]');
    if(!button||!tabs.contains(button)||!sections.has(button.dataset.companyTab))return;
    const u=new URL(location.href);u.searchParams.set('section',button.dataset.companyTab);
    history.replaceState(history.state,'',u.pathname+u.search+u.hash);
  });
  if(first && sections.has(initialSection)){
    const b=tabs.querySelector('[data-company-tab="'+initialSection+'"]');
    if(b)b.click();
  }
  first=false;
  return true;
 }
 if(mount())return;
 const observer=new MutationObserver(()=>{if(mount())observer.disconnect()});
 observer.observe(app,{childList:true,subtree:true,attributes:true,attributeFilter:['data-sw110c-ready']});
 window.addEventListener('pagehide',()=>observer.disconnect(),{once:true});
})();
