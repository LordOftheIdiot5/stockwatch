/* Descriptive matched-period analysis. No forecasts, rankings or imputed prices. */
(function(global){"use strict";
const DAY=86400000,MIN_MATCHES=60,MIN_EVENTS=10;
const KEYS=["numbers","prices","operations","potential","risk"];
const finite=x=>typeof x==="number"&&Number.isFinite(x);
const day=x=>typeof x==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x;
const safe=x=>{try{const u=new URL(x);return u.protocol==="https:"&&!u.username&&!u.password}catch{return false}};
const authorized=d=>d&&d.redistributionPermitted===true&&d.derivedResearchPermitted===true&&safe(d.sourceUrl)&&safe(d.licenseReference)&&typeof d.source==="string"&&d.source.trim();
function clean(rows,key,volume=false){
 if(!Array.isArray(rows))return [];
 const counts=new Map(),valid=new Map();
 for(const row of rows){
  if(!row||!day(row.date)||row.date>=new Date().toISOString().slice(0,10))continue;
  counts.set(row.date,(counts.get(row.date)||0)+1);
  const value=row[key];if(finite(value)&&value>0&&(!volume||(finite(row.volume)&&row.volume>0)))valid.set(row.date,{date:row.date,value});
 }
 return [...valid.values()].filter(x=>counts.get(x.date)===1).sort((a,b)=>a.date.localeCompare(b.date));
}
function equity(d,id){
 if(!authorized(d)||!id||(d.ticker||d.listingId)!==id||d.adjusted!==true||!(/^[A-Z]{3}$/.test(d.currency||"")))return [];
 return clean(d.bars,"close",true);
}
const days=(a,b)=>(Date.parse(b)-Date.parse(a))/DAY;
function aligned(stock,factor){
 const m=new Map(factor.map((p,i)=>[p.date,i])),out=[];
 for(let i=1;i<stock.length;i++){
  const a=stock[i-1],b=stock[i],j=m.get(b.date);
  if(j===undefined||j<1||factor[j-1].date!==a.date||days(a.date,b.date)>4)continue;
  out.push({date:b.date,x:Math.log(b.value/a.value),y:Math.log(factor[j].value/factor[j-1].value)});
 }
 return out;
}
function corr(rows){
 if(rows.length<30)return null;
 const mx=rows.reduce((s,p)=>s+p.x,0)/rows.length,my=rows.reduce((s,p)=>s+p.y,0)/rows.length;
 let xy=0,xx=0,yy=0;
 for(const p of rows){const x=p.x-mx,y=p.y-my;xy+=x*y;xx+=x*x;yy+=y*y}
 return xx>1e-20&&yy>1e-20?Math.max(-1,Math.min(1,xy/Math.sqrt(xx*yy))):null;
}
function association(stock,factor){
 const rows=aligned(stock,factor),n=rows.length,half=Math.floor(n/2);
 const base={n,first:rows[0]?.date||null,last:rows.at(-1)?.date||null};
 if(n<MIN_MATCHES)return {...base,status:"insufficient_overlap"};
 const r=corr(rows),early=corr(rows.slice(0,half)),late=corr(rows.slice(half));
 if([r,early,late].some(x=>x===null))return {...base,status:"constant_series"};
 return {...base,status:"descriptive",r,early,late,stableDirection:Math.sign(early)===Math.sign(late)&&Math.abs(early)>=.1&&Math.abs(late)>=.1};
}
function median(xs){const s=[...xs].sort((a,b)=>a-b),i=Math.floor(s.length/2);return s.length%2?s[i]:(s[i-1]+s[i])/2}
function eventWindows(stock,bench,events){
 const bm=new Map(bench.map((x,i)=>[x.date,i])),groups=new Map(),ids=new Set();
 for(const e of events||[]){
  if(!e||!day(e.date)||!e.id||ids.has(e.id)||!["strong","mentioned"].includes(e.confidence)||!safe(e.url))continue;
  ids.add(e.id);if(!groups.has(e.date))groups.set(e.date,[]);groups.get(e.date).push(e);
 }
 const windows=[];
 for(const [date,rows] of [...groups].sort(([a],[b])=>a.localeCompare(b))){
  const j=stock.findIndex(p=>p.date>=date),k=stock.findIndex(p=>p.date>date);
  if(j<=0||k<0)continue;
  const left=j-1,right=k,a=stock[left],b=stock[right];
  if(days(a.date,date)>4||days(date,b.date)>4||right-left>2)continue;
  const bl=bm.get(a.date),br=bm.get(b.date);
  if(bl===undefined||br===undefined||br-bl!==right-left||stock.slice(left,right+1).some((p,i)=>bench[bl+i]?.date!==p.date))continue;
  const tags=rows.length===1&&rows[0].confidence==="strong"&&rows[0].driverVersion===1?rows[0].driverTags||[]:[];
  const topic=tags.length===1&&KEYS.includes(tags[0].driver)&&typeof tags[0].basis==="string"?tags[0].driver:null;
  windows.push({date,left,right,start:a.date,end:b.date,topic,eventId:rows[0].id,
   relativePct:100*((b.value/a.value-1)-(bench[br].value/bench[bl].value-1))});
 }
 // Exclude every overlapping window, including windows with ambiguous topics.
 // This does not prove an absence of unobserved or same-period catalysts.
 return windows.filter((w,i)=>w.topic&&!windows.some((v,j)=>j!==i&&v.left<=w.right&&v.right>=w.left));
}
function eventSummary(stock,bench,events){
 const windows=eventWindows(stock,bench,events);
 return KEYS.map(key=>{const a=windows.filter(w=>w.topic===key),n=a.length;
  return {key,n,status:n>=MIN_EVENTS?"descriptive":"insufficient_events",
   ...(n>=MIN_EVENTS?{medianRelativePct:median(a.map(x=>x.relativePct)),positiveShare:a.filter(x=>x.relativePct>0).length/n,first:a[0].start,last:a.at(-1).end}:{} )};
 });
}
function configEntry(registry,id){
 if(registry?.schemaVersion!==1||!Object.hasOwn(registry.listings||{},id))return null;
 const e=registry.listings[id];return e&&e.identityReviewed===true&&typeof e.mic==="string"?e:null;
}
function validPath(p){return typeof p==="string"&&/^data\/sensitivity-inputs\/[A-Za-z0-9_-]{1,80}\.json$/.test(p)}
async function analyze({id,history,events,load}){
 const stock=equity(history,id);
 if(!stock.length)return {status:"history_required",observations:0};
 if(stock.length<MIN_MATCHES+1)return {status:"insufficient_history",observations:stock.length};
 let config;
 try{config=configEntry(await load("data/sensitivity-inputs-v1.json"),id)}catch{}
 if(!config)return {status:"inputs_required",observations:stock.length};
 const out={status:"available",observations:stock.length,factors:[],eventTopics:[],benchmark:null};
 for(const descriptor of Array.isArray(config.factors)?config.factors:[]){
  if(!descriptor?.id||!validPath(descriptor.path))continue;
  try{const d=await load(descriptor.path);if(!authorized(d)||d.seriesId!==descriptor.id||d.frequency!=="business_day"||d.changeMethod!=="log_return"||typeof d.unit!=="string")continue;
   const factor=clean(d.observations,"value");out.factors.push({id:descriptor.id,label:d.label||descriptor.id,unit:d.unit,source:d.source,sourceUrl:d.sourceUrl,licenseReference:d.licenseReference,...association(stock,factor)});
  }catch{}
 }
 const b=config.benchmark;
 if(b?.id&&validPath(b.path)){
  try{const d=await load(b.path);if(authorized(d)&&d.seriesId===b.id&&d.kind==="market_benchmark"&&d.mic===config.mic&&d.currency===history.currency&&d.adjusted===true&&d.frequency==="business_day"){
    const benchmark=clean(d.observations,"value");out.benchmark={label:d.label||b.id,source:d.source,sourceUrl:d.sourceUrl,licenseReference:d.licenseReference};out.eventTopics=eventSummary(stock,benchmark,events);
  }}catch{}
 }
 return out;
}
function render(host,result){
 if(!host)return;
 const n=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x};
 const link=(label,url)=>{const x=n("a",label,"sw-textlink");x.href=url;x.rel="noopener noreferrer";x.target="_blank";return x};
 host.replaceChildren(n("h3","Historical price sensitivity"),n("p","Historical association, not causation or a forecast. Only explicitly authorized adjusted histories enter the analysis.","sw-meta"));
 const statuses={history_required:"Awaiting licensed adjusted share-price history and explicit derived-analysis rights.",insufficient_history:"At least 61 valid dated closes are required before comparisons can begin.",inputs_required:"Awaiting reviewed benchmark and factor-series mappings for this listing."};
 if(result.status!=="available"){host.append(n("p",statuses[result.status]||"Checking historical coverage…","sw-meta"));if(result.observations)host.append(n("p",result.observations+" eligible closes","sw-meta"));return}
 host.append(n("p",result.observations+" eligible adjusted closes · matched intervals only","sw-meta"),n("h4","Economic factor associations"));
 if(!result.factors.length)host.append(n("p","No approved factor series is connected.","sw-meta"));
 const fmt=x=>x.toFixed(2);
 for(const d of result.factors){const row=n("div",undefined,"sw-peer");row.append(n("strong",d.label),n("small",d.n+" aligned return intervals · "+(d.first||"—")+" to "+(d.last||"—")));
  if(d.status==="descriptive")row.append(n("span","Correlation "+fmt(d.r)+" · early "+fmt(d.early)+" · late "+fmt(d.late)),n("small",d.stableDirection?"Same direction across both halves":"Weak or changing direction across halves"));
  else row.append(n("small","Insufficient aligned data or variation for a correlation."));
  row.append(link(d.source+" ↗",d.sourceUrl),link("Reuse terms ↗",d.licenseReference));host.append(row);
 }
 host.append(n("h4","Issuer-announcement windows"));
 if(!result.benchmark)host.append(n("p","Awaiting an approved same-market, same-currency adjusted benchmark.","sw-meta"));
 else{host.append(link(result.benchmark.label+" ↗",result.benchmark.sourceUrl),link("Benchmark reuse terms ↗",result.benchmark.licenseReference),n("p","Prior close before publication UTC day to first close after it; overlapping and multi-topic windows excluded. Difference from benchmark return, not a model-based abnormal return.","sw-meta"));
  for(const d of result.eventTopics){const row=n("div",undefined,"sw-peer");row.append(n("strong",d.key[0].toUpperCase()+d.key.slice(1)),n("small",d.n+" nonoverlapping eligible windows"));
   if(d.status==="descriptive")row.append(n("span","Median market-relative move "+fmt(d.medianRelativePct)+" percentage points"),n("small",Math.round(d.positiveShare*100)+"% positive relative moves · "+d.first+" to "+d.last));
   else row.append(n("small","At least 10 eligible windows needed."));host.append(row)}
 }
}
const api={clean,equity,aligned,association,eventWindows,eventSummary,configEntry,analyze,render};
if(typeof module==="object"&&module.exports)module.exports=api;else global.StockwatchSensitivity=api;
})(typeof window!=="undefined"?window:{});
