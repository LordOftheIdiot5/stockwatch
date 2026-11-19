/* Interactive research navigation. No causal scoring, inferred exposures or forecasts. */
(function(global){"use strict";
const defs=[
 {id:"numbers",label:"Numbers",sub:"Financial results",description:"Reported earnings, guidance, balance sheet and dividends.",sections:[["financials","Financial statements"],["events","Corporate events"]],news:["Earnings / results","Guidance"],groups:[]},
 {id:"prices",label:"Prices",sub:"Markets & costs",description:"Investigate commodity, energy, currency and financing context. Sector context is not a measured company exposure.",sections:[["chart","Price & activity"],["drivers","All industry drivers"]],news:[],groups:["Inputs","Markets"]},
 {id:"operations",label:"Operations",sub:"Assets & records",description:"Production, assets, infrastructure and operating metrics. Distinguish company disclosures from regional context.",sections:[["drivers","Industry drivers"]],news:[],groups:["Infrastructure"]},
 {id:"potential",label:"Potential",sub:"Projects & demand",description:"Reported contracts, investments, demand and strategic developments; not a prediction of future returns.",sections:[["filings","Company updates"]],news:["Contracts","M&A"],groups:["Demand"]},
 {id:"attention",label:"Attention",sub:"News & narratives",description:"Recent source-linked coverage. Volume of coverage is not sentiment, hype or evidence of a causal price move.",sections:[["filings","Company updates"]],news:null,groups:[]},
 {id:"risk",label:"Risk",sub:"External factors",description:"Research external risks and sector constraints. No probability or downside estimate is inferred.",sections:[["drivers","Industry drivers"],["events","Corporate events"]],news:[],groups:["Risk"]}
];
function nodes(ticker){
 return defs.map(d=>({...d,sub:ticker==="NHY.OL"&&d.id==="prices"?"Materials & power":ticker==="NHY.OL"&&d.id==="operations"?"Hydro assets & production":d.sub}));
}
function resolveProfile(registry,key){
 if(registry?.schemaVersion!==1||!Object.hasOwn(registry.profiles||{},key))return null;
 const p=registry.profiles[key],drivers=p?.drivers;
 if(!drivers||!defs.every(d=>{const v=drivers[d.id],s=registry.sources?.[v?.source];return v&&typeof v.sub==="string"&&typeof v.description==="string"&&safe(s?.url)&&Array.isArray(v.datasetIds)}))return null;
 return {name:p.name,drivers:Object.fromEntries(defs.map(d=>{const v=drivers[d.id],m=v.metric,valid=m&&Number.isFinite(m.value)&&typeof m.label==="string"&&typeof m.unit==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(m.periodEnd);return [d.id,{...v,metric:valid?m:null,evidence:registry.sources[v.source]}]}))};
}
function selectNews(items,driver){
 if(!driver)return [];
 return (Array.isArray(items)?items:[]).filter(x=>x&&typeof x.headline==="string"&&["strong","mentioned"].includes(x.confidence)&&(driver.id==="attention"||(x.driverVersion===1?x.driverTags?.some(t=>t.driver===driver.id):driver.news===null||driver.news.includes(x.category)))&&safe(x.url)).slice(0,5);
}
function safe(url){try{const u=new URL(url);return u.protocol==="https:"&&!u.username&&!u.password}catch{return false}}
function mount(host,{company,config,load,events=[],sections=null}){
 if(!host||!company)return null;
 const n=(tag,txt,cls)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=txt;if(cls)e.className=cls;return e};
 const btn=(txt,cls)=>{const e=n("button",txt,cls);e.type="button";return e};
 const a=(txt,url)=>{const e=n("a",txt,"sw-textlink");e.href=url;e.target="_blank";e.rel="noopener noreferrer";return e};
 let all=nodes(company.ticker),profile=null;const buttons=new Map();let selected="prices",currentEvents=events;const key=company.driverKey||company.ticker;
 const root=n("div",undefined,"sw88-driver"),head=n("div",undefined,"sw-section-row");const status=n("small","Sector context · no driver ranking yet");head.append(n("h2","Company intelligence map"),status);root.append(head,n("p","Choose a driver to explore evidence, linked datasets and existing research sections.","sw-meta"));
 const map=n("div",undefined,"sw88-map");map.setAttribute("aria-label","Company research categories");
 const center=n("div",undefined,"sw88-center");center.append(n("strong",company.name),n("small",company.ticker));map.append(center);
 for(const d of all){const b=btn(undefined,"sw88-node");b.dataset.driverNode=d.id;b.setAttribute("aria-controls","sw88-driver-detail");b.append(n("strong",d.label),n("small",d.sub));b.onclick=()=>draw(d.id);buttons.set(d.id,b);map.append(b)}
 root.append(map);
 const panel=n("section",undefined,"sw88-detail");panel.id="sw88-driver-detail";root.append(panel);host.replaceChildren(root);
 function draw(id){
  const d=all.find(x=>x.id===id);if(!d)return;selected=id;
  for(const [key,b] of buttons)b.setAttribute("aria-pressed",String(key===id));
  panel.replaceChildren(n("h3",d.label+" · "+d.sub),n("p",d.description,"sw-meta"));
  if(d.evidence){panel.append(a("Issuer evidence · "+d.evidence.label+" ↗",d.evidence.url));if(d.metric){const card=n("div",undefined,"sw-peer");card.append(n("small",d.metric.label+" · reported period example"),n("strong",d.metric.value.toLocaleString("en-GB",{maximumFractionDigits:3})+" "+d.metric.unit),n("small","Period ended "+d.metric.periodEnd+" · not necessarily latest"));panel.append(card)}if(d.missing)panel.append(n("p","Coverage gap: "+d.missing,"sw-meta"));}
  const links=n("div",undefined,"sw-controls");
  for(const [key,label] of d.sections){const target=sections?.querySelector('[data-company-section="'+key+'"]');if(!target)continue;const b=btn(label+" ↗","sw-soft-btn");b.onclick=()=>target.scrollIntoView({block:"start",behavior:"auto"});links.append(b)}
  if(company.ticker==="NHY.OL"&&id==="operations"&&sections){const target=sections.querySelector('[data-company-section="ownership-pilot"]');if(target){const b=btn("Reported ownership & assets ↗","sw-soft-btn");b.onclick=()=>target.scrollIntoView({block:"start",behavior:"auto"});links.append(b)}}
  if(links.children.length)panel.append(links);
  if(profile&&d.datasetIds?.length&&global.StockwatchIndustry&&config){const contextual=n("div");panel.append(contextual);global.StockwatchIndustry.mount(contextual,{config:{...config,driverProfiles:[{sectors:[company.sector],drivers:[{category:"Context",label:"Explore related official observations",question:"Background series only; no measured company exposure or price impact.",missing:d.missing||"Issuer-level linkage not quantified.",datasetIds:d.datasetIds}]}]},sector:company.sector,ticker:company.ticker,load});}
  else if(!profile&&d.groups.length&&global.StockwatchIndustry&&config){
   const p=(config.driverProfiles||[]).find(x=>x.sectors?.includes(company.sector));
   const drivers=(p?.drivers||[]).filter(x=>d.groups.includes(x.category));
   if(drivers.length){const contextual=n("div");panel.append(contextual);global.StockwatchIndustry.mount(contextual,{config:{...config,driverProfiles:[{...p,drivers}]},sector:company.sector,ticker:company.ticker,load});}
  }
  const related=selectNews(currentEvents,d);
  const news=n("div",undefined,"sw88-news");news.append(n("h4",id==="attention"?"Latest source-linked updates":"Related news and filings"),n("p","Topic tags are based on headlines or filing forms, not measured price impact. Attention lists all relevant news; it does not measure hype.","sw-meta"));
  if(!related.length)news.append(n("p","No matching categorized records in the loaded company archive. Unclassified news remains in Company updates.","sw-meta"));
  for(const e of related){const row=n("div",undefined,"sw88-story");row.append(a(e.headline,e.url),n("small",e.date+" · "+e.publisher+" · "+(e.confidence==="strong"?"Issuer-confirmed":"Named reference")));const basis=e.driverVersion===1?e.driverTags?.find(t=>t.driver===id)?.basis:null;if(basis)row.append(n("small","Topic evidence: "+basis));news.append(row)}
  panel.append(news);
  panel.setAttribute("aria-label",d.label+" research detail");
 }
 draw(selected);
 if(typeof load==="function")Promise.resolve().then(()=>load("data/company-driver-profiles-v1.json")).then(registry=>{if(!host.contains(root))return;profile=resolveProfile(registry,key);if(!profile)return;all=nodes(company.ticker).map(d=>({...d,...profile.drivers[d.id]}));status.textContent="Issuer-reviewed business context · not price sensitivity";for(const d of all)buttons.get(d.id).querySelector("small").textContent=d.sub;draw(selected)}).catch(()=>{});
 return {updateEvents(items){currentEvents=items;draw(selected)},select:draw};
}
const api={nodes,resolveProfile,selectNews,mount};if(typeof module==="object"&&module.exports)module.exports=api;else global.StockwatchDriverMap=api;
})(typeof window!=="undefined"?window:{});
