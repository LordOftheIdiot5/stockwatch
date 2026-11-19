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
function selectNews(items,driver){
 if(!driver)return [];
 return (Array.isArray(items)?items:[]).filter(x=>x&&typeof x.headline==="string"&&["strong","mentioned"].includes(x.confidence)&&(driver.news===null||driver.news.includes(x.category))&&safe(x.url)).slice(0,5);
}
function safe(url){try{const u=new URL(url);return u.protocol==="https:"&&!u.username&&!u.password}catch{return false}}
function mount(host,{company,config,load,events=[],sections=null}){
 if(!host||!company)return null;
 const n=(tag,txt,cls)=>{const e=document.createElement(tag);if(txt!==undefined)e.textContent=txt;if(cls)e.className=cls;return e};
 const btn=(txt,cls)=>{const e=n("button",txt,cls);e.type="button";return e};
 const a=(txt,url)=>{const e=n("a",txt,"sw-textlink");e.href=url;e.target="_blank";e.rel="noopener noreferrer";return e};
 const all=nodes(company.ticker),buttons=new Map();let selected="prices",currentEvents=events;
 const root=n("div",undefined,"sw88-driver"),head=n("div",undefined,"sw-section-row");head.append(n("h2","Company intelligence map"),n("small","Research context · no driver ranking yet"));root.append(head,n("p","Choose a driver to explore evidence, linked datasets and existing research sections.","sw-meta"));
 const map=n("div",undefined,"sw88-map");map.setAttribute("aria-label","Company research categories");
 const center=n("div",undefined,"sw88-center");center.append(n("strong",company.name),n("small",company.ticker));map.append(center);
 for(const d of all){const b=btn(undefined,"sw88-node");b.dataset.driverNode=d.id;b.setAttribute("aria-controls","sw88-driver-detail");b.append(n("strong",d.label),n("small",d.sub));b.onclick=()=>draw(d.id);buttons.set(d.id,b);map.append(b)}
 root.append(map);
 const panel=n("section",undefined,"sw88-detail");panel.id="sw88-driver-detail";root.append(panel);host.replaceChildren(root);
 function draw(id){
  const d=all.find(x=>x.id===id);if(!d)return;selected=id;
  for(const [key,b] of buttons)b.setAttribute("aria-pressed",String(key===id));
  panel.replaceChildren(n("h3",d.label+" · "+d.sub),n("p",d.description,"sw-meta"));
  const links=n("div",undefined,"sw-controls");
  for(const [key,label] of d.sections){const target=sections?.querySelector('[data-company-section="'+key+'"]');if(!target)continue;const b=btn(label+" ↗","sw-soft-btn");b.onclick=()=>target.scrollIntoView({block:"start",behavior:"auto"});links.append(b)}
  if(company.ticker==="NHY.OL"&&id==="operations"&&sections){const target=sections.querySelector('[data-company-section="ownership-pilot"]');if(target){const b=btn("Reported ownership & assets ↗","sw-soft-btn");b.onclick=()=>target.scrollIntoView({block:"start",behavior:"auto"});links.append(b)}}
  if(links.children.length)panel.append(links);
  if(d.groups.length&&global.StockwatchIndustry&&config){
   const p=(config.driverProfiles||[]).find(x=>x.sectors?.includes(company.sector));
   const drivers=(p?.drivers||[]).filter(x=>d.groups.includes(x.category));
   if(drivers.length){const contextual=n("div");panel.append(contextual);global.StockwatchIndustry.mount(contextual,{config:{...config,driverProfiles:[{...p,drivers}]},sector:company.sector,ticker:company.ticker,load});}
  }
  const related=selectNews(currentEvents,d);
  const news=n("div",undefined,"sw88-news");news.append(n("h4",id==="attention"?"Latest source-linked updates":"Related news and filings"));
  if(!related.length)news.append(n("p","No matching categorized records in the loaded company archive. Unclassified news remains in Company updates.","sw-meta"));
  for(const e of related){const row=n("div",undefined,"sw88-story");row.append(a(e.headline,e.url),n("small",e.date+" · "+e.publisher+" · "+(e.confidence==="strong"?"Issuer-confirmed":"Named reference")));news.append(row)}
  panel.append(news);
  panel.setAttribute("aria-label",d.label+" research detail");
 }
 draw(selected);
 return {updateEvents(items){currentEvents=items;draw(selected)},select:draw};
}
const api={nodes,selectNews,mount};if(typeof module==="object"&&module.exports)module.exports=api;else global.StockwatchDriverMap=api;
})(typeof window!=="undefined"?window:{});
