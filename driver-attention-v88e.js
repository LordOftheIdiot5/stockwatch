/* Inspect observed archive coverage; no sentiment or forecast scoring. */
(function(global){"use strict";
const safe=x=>{try{const u=new URL(x);return u.protocol==="https:"&&!u.username&&!u.password}catch{return false}};
const count=x=>Number.isInteger(x)&&x>=0;
const day=x=>typeof x==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x;
function select(data,key){
 if(data?.schemaVersion!==1||!Object.hasOwn(data.listings||{},key)||!Number.isFinite(Date.parse(data.generated)))return null;
 const r=data.listings[key],d=r?.daily;
 if(r?.listingId!==key||!Array.isArray(d)||d.length!==14||!count(r.observedRecords)||!d.every((x,i)=>day(x.date)&&count(x.issuer)&&count(x.media)&&(!i||Date.parse(x.date)-Date.parse(d[i-1].date)===86400000))||d[0].date!==data.windowStart||d[13].date!==data.windowEnd||Date.parse(d[13].date)>=Date.parse(data.generated.slice(0,10)))return null;
 const sum=a=>({issuer:a.reduce((s,x)=>s+x.issuer,0),media:a.reduce((s,x)=>s+x.media,0)});
 const potential=(Array.isArray(r.potential)?r.potential:[]).filter(x=>x&&safe(x.url)&&["issuer","named_reference"].includes(x.evidence)&&typeof x.headline==="string"&&typeof x.topic==="string"&&Number.isFinite(Date.parse(x.published))&&Date.parse(x.published)<=Date.parse(data.generated));
 return {...r,generated:data.generated,prior7:sum(d.slice(0,7)),recent7:sum(d.slice(7)),potential};
}
function render(host,r,mode){
 if(!host)return;
 const n=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x};
 host.replaceChildren(n("h4",mode==="attention"?"Observed news attention":"Future developments · evidence watch"));
 if(!r){host.append(n("p","No archive attention snapshot available for this listing. This is not a measure of market interest or a lack of opportunities.","sw-meta"));return}
 host.append(n("p","Archive snapshot: "+r.generated.slice(0,16).replace("T"," ")+" UTC · "+r.observedRecords+" eligible retained records. Coverage is incomplete; not a measure of market-wide interest.","sw-meta"));
 if(Date.now()-Date.parse(r.generated)>3*86400000)host.append(n("p","Older saved snapshot; collection freshness not confirmed.","sw-meta"));
 if(mode==="attention"){
  const summary=n("div",undefined,"sw88-attention-summary");
  for(const [k,label] of [["issuer","Issuer-confirmed disclosures"],["media","Named media references"]]){
   const cell=n("div",undefined,"sw-peer"),delta=r.recent7[k]-r.prior7[k];
   cell.append(n("small",label),n("strong",String(r.recent7[k])+" retained records"),n("span","Prior 7 days: "+r.prior7[k]+" · difference "+(delta>0?"+":"")+delta));summary.append(cell);
  }
  host.append(summary,n("p","14 completed UTC days · "+r.daily[0].date+" to "+r.daily[13].date,"sw-meta"));
  const graph=n("div",undefined,"sw88-attention-bars");graph.setAttribute("role","group");graph.setAttribute("aria-label","Daily retained news counts");
  const max=Math.max(1,...r.daily.map(x=>x.issuer+x.media));
  for(const d of r.daily){const col=n("div",undefined,"sw88-attention-day"),b=n("div",undefined,"sw88-attention-bar"),label=d.date+": "+d.issuer+" issuer, "+d.media+" named references";col.title=label;b.setAttribute("aria-label",label);b.setAttribute("role","img");
   for(const [key,cls] of [["media","media"],["issuer","issuer"]]){const block=n("span",undefined,cls);block.style.height=(100*d[key]/max)+"%";b.append(block)}
   col.append(b,n("small",d.date.slice(8)));graph.append(col);
  }
  host.append(graph,n("p","Teal: issuer disclosures · blue: named media references. Zero means no retained matches, not no news. Differences can reflect collector changes or outages. No hype or sentiment score.","sw-meta"));
 }else{
  for(const [evidence,label] of [["issuer","Issuer-confirmed source records"],["named_reference","Named references · verify original source"]]){
   host.append(n("h4",label));const rows=r.potential.filter(x=>x.evidence===evidence).slice(0,5);
   if(!rows.length)host.append(n("p","No retained matching topic records in this snapshot.","sw-meta"));
   for(const x of rows){const item=n("div",undefined,"sw88-story"),a=n("a",x.headline,"sw-textlink");a.href=x.url;a.target="_blank";a.rel="noopener noreferrer";item.append(a,n("small",x.published.slice(0,10)+" · "+x.topic));host.append(item)}
  }
  host.append(n("p","Selected potential-related headlines from the past 90 days, at most 20 retained candidates per listing before display. These are topic leads, not verified project stages, expected revenue or upside estimates.","sw-meta"));
 }
}
const api={select,render};if(typeof module==="object"&&module.exports)module.exports=api;else global.StockwatchAttention=api;
})(typeof window!=="undefined"?window:{});
