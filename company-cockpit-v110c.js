/* V110c — source-backed single-focus company research cockpit.
 * Enhances real V94 company sections; never creates new prices or financial
 * facts. The full original report remains available in one click.
 */
(function(){
'use strict';
if(document.body?.dataset.page!=='company')return;
const root=document.getElementById('v4app');
if(!root)return;
const names=new Set(['chart','financials','filings','peers','events','drivers','identity']);
function el(tag,cls,text){
 const node=document.createElement(tag);
 if(cls)node.className=cls;
 if(text!==undefined)node.textContent=text;
 return node;
}
function mount(){
 const panel=root.querySelector('.sw-company-research');
 if(!panel||panel.dataset.sw94Ready!=='true'||panel.dataset.sw110cReady==='true')return;
 const nav=panel.querySelector('.sw-company-tabs');
 const content=panel.querySelector(':scope > .sw-panel-pad');
 if(!nav||!content)return;
 const tabs=[...nav.querySelectorAll('[data-company-tab]')]
   .filter(button=>names.has(button.dataset.companyTab)&&
     panel.querySelector('[data-company-section="'+button.dataset.companyTab+'"]'));
 if(tabs.length!==7)return;
 panel.dataset.sw110cReady='true';
 const mode=el('button','sw110c-mode','Full report');
 mode.type='button';mode.setAttribute('aria-pressed','false');
 mode.setAttribute('aria-label','Expand all company research sections');
 nav.append(mode);
 const advanced=[...content.children].filter(n=>n.nodeType===1&&
   !n.matches('[data-company-section],#companyDriverMap'));
 const extra=el('details','sw110c-more');
 const heading=el('summary','','Additional company evidence and operating models');
 const note=el('p','sw-meta',
   'Original calculations and sourced analysis are retained. Availability depends on this issuer.');
 const inner=el('div','sw110c-more-inner');
 extra.append(heading,note,inner);
 for(const node of advanced)inner.append(node);
 if(advanced.length)content.append(extra);
 const sections=new Map(tabs.map(b=>[b.dataset.companyTab,
   panel.querySelector('[data-company-section="'+b.dataset.companyTab+'"]')]));
 const info=el('p','sw110c-hint',
   'Choose a research section. Data and source dates are unchanged; use Full report to read everything.');
 nav.after(info);
 function focus(key){
   if(!sections.has(key))return;
   panel.dataset.sw110cTab=key;
   for(const [name,section] of sections) section.hidden=name!==key;
   if(panel.dataset.sw110cMode==='focus'){
     for(const b of tabs){
       const selected=b.dataset.companyTab===key;
       b.classList.toggle('sw94-current',selected);
       if(selected)b.setAttribute('aria-current','location');
       else b.removeAttribute('aria-current');
       b.setAttribute('aria-pressed',String(selected));
     }
   }
 }
 function setMode(full){
   panel.dataset.sw110cMode=full?'full':'focus';
   panel.classList.toggle('sw110c-full',full);
   mode.textContent=full?'Focused view':'Full report';
   mode.setAttribute('aria-pressed',String(full));
   mode.setAttribute('aria-label',full?'Show focused company research section':'Expand all company research sections');
   info.textContent=full?
     'Full source-backed report. Select a section above or choose Focused view for a compact workspace.':
     'Choose a research section. Data and source dates are unchanged; use Full report to read everything.';
   if(full){
     for(const section of sections.values())section.hidden=false;
     if(advanced.length)extra.open=true;
   }else{
     if(advanced.length)extra.open=false;
     focus(panel.dataset.sw110cTab||'chart');
   }
 }
 // Capture phase precedes v4's existing jump handler, so a formerly hidden
 // panel is made visible before scrollIntoView. It also preserves V94 keyboard.
 nav.addEventListener('click',event=>{
   const button=event.target.closest('[data-company-tab]');
   if(!button||!nav.contains(button))return;
   if(panel.dataset.sw110cMode==='focus')focus(button.dataset.companyTab);
 },true);
 panel.addEventListener('click',event=>{
   const anchor=event.target.closest('a[href^="#sw94-company-"]');
   if(!anchor)return;
   const key=anchor.hash.slice('#sw94-company-'.length);
   if(panel.dataset.sw110cMode==='focus')focus(key);
 },true);
 mode.addEventListener('click',()=>setMode(panel.dataset.sw110cMode!=='full'));
 setMode(false);
 focus('chart');
}
mount();
let scheduled=false;
const observer=new MutationObserver(()=>{
 if(scheduled)return;
 scheduled=true;
 requestAnimationFrame(()=>{scheduled=false;mount()});
});
observer.observe(root,{subtree:true,childList:true});
})();
