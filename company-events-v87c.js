/* Source-linked company event lens. No price, sentiment or causal inference. */
(function(global){
"use strict";
const utcDay=s=>{if(typeof s!=="string"||!/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(s)||!Number.isFinite(Date.parse(s)))return null;return new Date(s).toISOString().slice(0,10)};
const safe=u=>{try{return new URL(u).protocol==="https:"}catch{return false}};
function select(items,{ticker,cik=null}={}){
 const seen=new Set(),out=[];
 for(const x of Array.isArray(items)?items:[]){
  if(!x||x.ticker!==ticker||x.duplicateOf||!["strong","mentioned"].includes(x.relevance)||!safe(x.url)||typeof x.headline!=="string"||!x.headline.trim())continue;
  // SEC filings are joined only via both verified CIK and ticker. Bare symbols
  // are never joined to non-US listings or to news with unclear provenance.
  if(cik){if(x.sourceFeed!=="sec_edgar"||x.sourceIssuer!==cik||x.match!=="issuer_code")continue}
  else if(x.sourceFeed==="sec_edgar")continue;
  const day=utcDay(x.published);if(!day||day>new Date().toISOString().slice(0,10)||!x.id||seen.has(x.id))continue;
  seen.add(x.id);out.push({id:x.id,date:day,published:x.published,headline:x.headline,category:x.category||"General",publisher:x.publisher||"Source",url:x.url,confidence:x.relevance,form:x.form||null,driverVersion:x.driverVersion||null,driverTags:Array.isArray(x.driverTags)?x.driverTags.filter(t=>t&&["numbers","prices","operations","potential","risk"].includes(t.driver)&&typeof t.basis==="string"):[]});
 }
 return out.sort((a,b)=>Date.parse(b.published)-Date.parse(a.published)||a.id.localeCompare(b.id));
}
let archivePromise;
function load(loader){
 if(!archivePromise)archivePromise=Promise.resolve().then(()=>loader("data/news-archive.json")).then(d=>{if(!Array.isArray(d?.items))throw Error("invalid archive");return d.items}).catch(e=>{archivePromise=null;throw e});
 return archivePromise;
}
function mount(host,events,{sourceStatus="Rolling archive",onDate=null}={}){
 if(!host)return;
 const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n};
 const heading=el("div",undefined,"sw-section-row");heading.append(el("h2","Company event lens"),el("small",events.length+" source-linked records · "+sourceStatus));host.replaceChildren(heading);
 host.append(el("p","Publication dates (UTC), not trading-session reaction dates. Issuer-confirmed filings and named media references are distinct. Timing alone does not establish price impact.","sw-meta"));
 const controls=el("div",undefined,"sw-controls"),filter=el("select"),prev=el("button","Previous","sw-soft-btn"),next=el("button","Next","sw-soft-btn"),count=el("span",undefined,"sw-meta"),list=el("div");filter.setAttribute("aria-label","Filter company event evidence");for(const [v,t] of [["all","All relevant events"],["strong","Issuer-confirmed filings"],["mentioned","Named media references"]]){const o=el("option",t);o.value=v;filter.append(o)}prev.type=next.type="button";controls.append(filter,prev,count,next);host.append(controls,list);let page=0;
 const draw=()=>{const rows=events.filter(e=>filter.value==="all"||e.confidence===filter.value),pages=Math.max(1,Math.ceil(rows.length/6));page=Math.min(page,pages-1);prev.disabled=page===0;next.disabled=page>=pages-1;count.textContent="Page "+(page+1)+" / "+pages+" · "+rows.length+" records";list.replaceChildren();
  if(!rows.length)list.append(el("p","No matching verified or named events in this snapshot.","sw-meta"));
  for(const e of rows.slice(page*6,page*6+6)){const item=el("div",undefined,"sw-peer");const a=el("a",e.headline);a.href=e.url;a.target="_blank";a.rel="noopener noreferrer";item.append(el("small",e.date+" UTC · "+e.category+" · "+(e.confidence==="strong"?"Issuer-confirmed":"Named reference")),a,el("span",e.publisher+" · "+e.published));if(onDate){const b=el("button","Inspect chart date","sw-soft-btn");b.type="button";const msg=el("span",undefined,"sw-meta");msg.setAttribute("role","status");b.onclick=()=>{msg.textContent=onDate(e.date)?"Chart selected: "+e.date:"No licensed price observation for this publication date.";};item.append(b,msg)}list.append(item)}
 };
 filter.onchange=()=>{page=0;draw()};prev.onclick=()=>{page=Math.max(0,page-1);draw()};next.onclick=()=>{page++;draw()};draw();
}
const api={select,utcDay,load,mount};if(typeof module==="object"&&module.exports)module.exports=api;else global.StockwatchCompanyEvents=api;
})(typeof window!=="undefined"?window:{});
