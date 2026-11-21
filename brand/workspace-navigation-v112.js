/* V112 — consistent navigation on reference, data, discovery and About routes.
   Presentation-only: never changes quotes, events, search results or source rights. */
(() => {
 'use strict';
 const body=document.body;
 if(!body.classList.contains('sw-brand-v47'))return;
 const pages={
  'directory.html':'directory','research.html':'research','search.html':'search',
  'data-products.html':'data-products','welcome.html':'welcome'
 };
 const route=location.pathname.split('/').pop()||'index.html';
 if(!pages[route])return;
 body.dataset.page=pages[route];
 body.classList.add('sw112-connected');
 const header=body.querySelector(':scope > header');
 const main=body.querySelector(':scope > main');
 const nav=header?.querySelector(':scope > nav[aria-label="Main navigation"]');
 if(!main||!header||!nav)return;
 if(!main.id)main.id='main-content';
 if(!main.hasAttribute('tabindex'))main.tabIndex=-1;
 if(!body.querySelector('a[href="#main-content"]')){
   const skip=document.createElement('a');
   skip.href='#main-content';
   skip.className='sw112-skip';
   skip.textContent='Skip to main content';
   body.insertBefore(skip,header);
 }
 const direct=href=>[...nav.querySelectorAll(':scope > a[href]')]
   .find(a=>a.getAttribute('href')===href);
 const overview=direct('index.html'),directory=direct('directory.html'),
       methodology=direct('research.html'),leivro=direct('https://leivro.com/');
 if(overview)overview.textContent='Overview';
 if(directory)directory.textContent='Instruments';
 if(methodology)methodology.textContent='Methodology';
 if(leivro)leivro.classList.add('sw112-external');
 const add=(href,label,after)=>{
  let a=direct(href);
  if(!a){a=document.createElement('a');a.href=href;a.textContent=label;
    a.className='sw112-task-link';after?.after(a)}
  return a;
 };
 const terminal=add('terminal.html','Terminal',overview);
 const stocks=add('stocks.html','Stocks',terminal);
 const search=add('search.html','Search',methodology||stocks);
 add('data-products.html','Data products',search);
 for(const a of nav.querySelectorAll(':scope > a[href]')){
  if(a.getAttribute('href')===route){a.classList.add('sw112-active');a.setAttribute('aria-current','page')}
  else {a.classList.remove('sw112-active');a.removeAttribute('aria-current')}
 }
 const brand=header.querySelector('a.brand');
 if(brand){brand.setAttribute('aria-label','Nordl Stockwatch — About');if(route==='welcome.html')brand.setAttribute('aria-current','page');}
 // The same research destinations are reachable in desktop and phone menus.
 for(const drawer of body.querySelectorAll('.sw-brand-drawer,.sw-mobile-drawer')){
  const platform=[...drawer.querySelectorAll(':scope > section')].find(s=>
    /DATA\s*&\s*PLATFORM/i.test(s.querySelector('p')?.textContent||''));
  const links=platform?.querySelector(':scope > div');
  if(!links)continue;
  for(const [href,title,glyph] of [
   ['search.html','Global research search','⌕'],
   ['data-products.html','Data products','▤']
  ]){
    if(links.querySelector('a[href="'+href+'"]'))continue;
    const a=document.createElement('a');a.href=href;a.className='sw-mobile-drawer-link sw112-injected-link';
    const icon=document.createElement('span');icon.className='sw-link-icon';
    icon.textContent=glyph;icon.setAttribute('aria-hidden','true');
    const caption=document.createElement('span');caption.textContent=title;
    a.append(icon,caption);links.append(a);
  }
 }
 const name={'directory.html':'Instrument directory','research.html':'Research methodology',
  'search.html':'Global research search','data-products.html':'Data products',
  'welcome.html':'About Stockwatch'}[route];
 for(const a of body.querySelectorAll('.sw-brand-drawer a[href],.sw-mobile-drawer a[href]')){
  if(a.getAttribute('href')===route){a.classList.add('active');a.setAttribute('aria-current','page')}
  else{a.classList.remove('active');a.removeAttribute('aria-current')}
 }
 const more=body.querySelector('.sw-mobile-more');
 if(more){
  more.classList.add('sw112-more-current');
  more.querySelector(':scope > summary')?.setAttribute('aria-label','More Stockwatch pages, current page: '+name);
 }
 for(const a of body.querySelectorAll('.sw-mobile-primary > a.sw-mobile-link')){
  a.classList.remove('active');a.removeAttribute('aria-current');
 }
 for(const details of body.querySelectorAll('.sw-brand-more,.sw-mobile-more')){
  details.addEventListener('keydown',event=>{
   if(event.key!=='Escape'||!details.open)return;
   event.preventDefault();details.open=false;
   details.querySelector(':scope > summary')?.focus();
  });
 }
 document.addEventListener('pointerdown',event=>{
  const desktop=header.querySelector('.sw-brand-more[open]');
  if(desktop&&!desktop.contains(event.target))desktop.open=false;
 });
})();