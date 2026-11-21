/* V110b: in-page navigation and reversible compact layout for source-backed pages.
   No feed requests, quote changes, or guessed source content. */
(function(){
 'use strict';
 const pages=new Set(['stocks','news','calendar','spreads','shipping',
   'commodities','intelligence','compare','health']);
 if(!pages.has(document.body?.dataset.page))return;
 const root=document.getElementById('v4app')||document.getElementById('app');
 if(!root||!root.parentNode)return;
 const nav=document.createElement('nav');nav.className='sw110b-jump';
 nav.setAttribute('aria-label','Research sections and layout density');
 const label=document.createElement('span');
 label.className='sw110b-jump-label';label.textContent='IN THIS VIEW';
 const links=document.createElement('div');links.className='sw110b-jump-links';
 const toggle=document.createElement('button');
 toggle.type='button';toggle.className='sw110b-layout-toggle';
 toggle.textContent='Full layout';toggle.setAttribute('aria-pressed','false');
 toggle.addEventListener('click',()=>{
   const spacious=document.body.classList.toggle('sw110b-spacious');
   toggle.textContent=spacious?'Compact layout':'Full layout';
   toggle.setAttribute('aria-pressed',String(spacious));
   toggle.setAttribute('aria-label',spacious?'Show compact research layout':'Show full research page layout');
 });
 nav.append(label,links,toggle);root.parentNode.insertBefore(nav,root);
 let signature='',scheduled=false;
 function refresh(){
   scheduled=false;if(!root.isConnected)return;
   const selected=[],names=new Set();
   for(const h of root.querySelectorAll('h2')){
     const title=(h.textContent||'').replace(/\s+/g,' ').trim();
     if(!title||title.length>43||names.has(title.toLowerCase()))continue;
     if(!h.getClientRects().length)continue;
     names.add(title.toLowerCase());selected.push({h,title});
     if(selected.length===7)break;
   }
   const key=selected.map(x=>x.title).join('|');
   if(key===signature)return;
   signature=key;links.replaceChildren();
   selected.forEach(({h,title},i)=>{
     const id='sw110b-research-section-'+i;
     h.id=id;h.classList.add('sw110b-section-target');
     const a=document.createElement('a');a.href='#'+id;a.textContent=title;links.append(a);
   });
 }
 function schedule(){if(scheduled)return;scheduled=true;requestAnimationFrame(refresh)}
 new MutationObserver(schedule).observe(root,{childList:true,subtree:true});
 refresh();
})();