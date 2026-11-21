/* V94 company research visual/navigation enhancement.
 * Original financial facts, company histories, source URLs and chart maths
 * stay with v4.js and existing provider-approved widgets.
 */
(function(factory){
"use strict";
const helpers=factory();
if(typeof module==="object"&&module.exports){module.exports=helpers;return;}
if(typeof document==="undefined")return;
const APP=document.getElementById("v4app");
if(!APP||document.body.dataset.page!=="company")return;
function enhance(){
 const panel=APP.querySelector(".sw-company-research");
 if(!panel){
  const ref=APP.querySelector(".sw-identity-grid");
  if(ref)APP.classList.add("sw94-reference-profile");
  return;
 }
 if(panel.dataset.sw94Ready==="true")return;
 panel.dataset.sw94Ready="true";
 APP.classList.add("sw94-company-profile");
 document.body.classList.add("sw94-profile-ready");
 const nav=panel.querySelector(".sw-company-tabs");
 const chart=panel.querySelector('[data-company-section="chart"]');
 const map=panel.querySelector("#companyDriverMap");
 // Lead with actual verified price-history state, then relationship/driver
 // research. Reparent the existing map node: no new data or SVG.
 if(chart&&map&&chart.parentElement)chart.insertAdjacentElement("afterend",map);
 if(!nav||!chart)return;
 nav.setAttribute("role","navigation");
 nav.setAttribute("aria-label","Jump between company research sections");
 const buttons=[...nav.querySelectorAll("[data-company-tab]")];
 const mapped=buttons.map(button=>{
   const id=helpers.sectionId(button.dataset.companyTab);
   const section=panel.querySelector('[data-company-section="'+button.dataset.companyTab+'"]');
   if(!id||!section)return null;
   section.id=id;
   button.setAttribute("aria-controls",id);
   button.setAttribute("aria-label","Jump to "+(button.textContent||"research section").trim());
   return {button,section};
 }).filter(Boolean);
 function activate(button){
   for(const item of mapped){
     const isCurrent=item.button===button;
     item.button.classList.toggle("sw94-current",isCurrent);
     if(isCurrent)item.button.setAttribute("aria-current","location");
     else item.button.removeAttribute("aria-current");
   }
 }
 if(mapped.length)activate(mapped[0].button);
 for(const item of mapped)item.button.addEventListener("click",()=>activate(item.button));
 // Keep the highlighted section aligned with the viewport, including when
 // users return to the top after jumping to Financials or Corporate events.
 let scrollQueued=false;
 const refreshSelection=()=>{
   scrollQueued=false;
   if(!panel.isConnected||!mapped.length)return;
   // V110c has genuine focused tabs; page scroll must not change the chosen tab.
   if(panel.dataset.sw110cMode==='focus')return;
   const threshold=Math.min(220,window.innerHeight*0.28);
   let current=mapped[0];
   for(const item of mapped){
     if(item.section.getBoundingClientRect().top<=threshold)current=item;
   }
   activate(current.button);
 };
 window.addEventListener("scroll",()=>{
   if(scrollQueued||!panel.isConnected)return;
   scrollQueued=true;
   requestAnimationFrame(refreshSelection);
 },{passive:true});
 nav.addEventListener("keydown",event=>{
   if(!["ArrowRight","ArrowLeft","Home","End"].includes(event.key))return;
   const i=mapped.findIndex(item=>item.button===document.activeElement);
   if(i<0||!mapped.length)return;
   const next=event.key==="Home"?0:event.key==="End"?mapped.length-1:
     (i+(event.key==="ArrowRight"?1:-1)+mapped.length)%mapped.length;
   event.preventDefault();
   mapped[next].button.focus();
 });
 const history=panel.querySelector("#companyHistorySource");
 if(history){
   history.setAttribute("role","status");
   history.setAttribute("aria-live","polite");
   history.setAttribute("aria-label","Available source-licensed historical observations");
 }
 const actualChart=panel.querySelector("#individualChart");
 if(actualChart){
   actualChart.setAttribute("role","region");
   actualChart.setAttribute("aria-label","Company price history when a licensed dated series exists");
 }
 // These links use existing public research pages; they do not imply that a
 // licensed price history is connected for the selected company.
 const links=document.createElement("nav");
 links.className="sw94-research-shortcuts";
 links.setAttribute("aria-label","Company research shortcuts");
 for(const item of [
   ["Financial statements","financials"],
   ["Source coverage","identity"],
   ["Company updates","filings"]
 ]){
   const id=helpers.sectionId(item[1]);
   if(!panel.querySelector("#"+id))continue;
   const a=document.createElement("a");
   a.href="#"+id;
   a.textContent=item[0];
   links.append(a);
 }
 if(links.childElementCount>0){
   chart.insertBefore(links,chart.firstChild);
 }
}
enhance();
const watcher=new MutationObserver(enhance);
watcher.observe(APP,{childList:true,subtree:true});
})(function(){
"use strict";
const allowed=new Set(["chart","financials","filings","peers","events","drivers","identity"]);
function sectionId(key){
 return typeof key==="string"&&allowed.has(key)?"sw94-company-"+key:null;
}
return {sectionId};
});
