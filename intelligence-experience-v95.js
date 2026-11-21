/* V95: accessible context for typed, existing intelligence graph.
 * No new relationships, cash-flow claims, market data fetches or storage.
 */
(function(factory){
 "use strict";
 const util=factory();
 if(typeof module==="object"&&module.exports){module.exports=util;return}
 if(typeof document==="undefined"||document.body.dataset.page!=="intelligence")return;
 const app=document.querySelector("#v4app");
 if(!app)return;
 let watching=false;
 function element(tag,text,cls){
   const el=document.createElement(tag);
   el.textContent=text;
   if(cls)el.className=cls;
   return el;
 }
 function enhance(){
   const map=document.querySelector("#intelMap");
   if(!map||!app.contains(map)||map.dataset.sw95Enhanced==="yes")return;
   map.dataset.sw95Enhanced="yes";
   map.setAttribute("role","region");
   map.setAttribute("aria-label","Selected instrument and typed evidence relationships");
   const legend=element("section","","sw95-graph-guide");
   legend.setAttribute("aria-label","How to read the relationships");
   legend.append(element("strong","How to read the graph"));
   const row=element("div","","sw95-graph-kinds");
   for(const [kind,description] of util.legend()){
     const pill=element("span",kind,"sw95-graph-kind");
     pill.setAttribute("title",description);
     row.append(pill);
   }
   legend.append(row);
   legend.append(element("p",util.disclaimer(),"sw95-graph-disclaimer"));
   map.before(legend);
   const search=document.getElementById("intelSearch");
   const select=document.getElementById("intelListing");
   if(search&&select){
     search.setAttribute("aria-controls",select.id);
     const status=element("p","Select an instrument to inspect its cited relationships.","sw95-graph-selection");
     status.id="sw95GraphSelection";
     status.setAttribute("role","status");
     status.setAttribute("aria-live","polite");
     legend.after(status);
     function refresh(){
       const label=select.selectedOptions?.[0]?.textContent?.trim()||"No matching instrument";
       status.textContent="Selected instrument: "+label+". Classification and context are not transactions.";
     }
     select.addEventListener("change",refresh);
     search.addEventListener("input",()=>queueMicrotask(refresh));
     refresh();
   }
 }
 enhance();
 if(!watching){
   watching=true;
   const observer=new MutationObserver(enhance);
   observer.observe(app,{subtree:true,childList:true});
 }
})(function(){
 "use strict";
 function legend(){return [
  ["Selected listing","Exact selected instrument record, not necessarily its issuer"],
  ["Relationship evidence","Typed listing, issuer or identifier evidence subject to validation"],
  ["Context and peers","Editorial classification or comparable instrument, not ownership"]
 ]}
 function disclaimer(){
   return "Connections indicate reference or source-linked research context. They do not prove supplier revenue, ownership, investment flows or trading exposure.";
 }
 return {legend,disclaimer};
});
