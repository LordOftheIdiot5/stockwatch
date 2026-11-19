(function(global){"use strict";
const safe=u=>{try{return new URL(u).protocol==="https:"}catch{return false}};
function select(d,ticker){
 if(d?.schemaVersion!==1||!Array.isArray(d.links)||d.assetSnapshot?.license!=="https://data.norge.no/nlod/"||!safe(d.assetSnapshot.source))return [];
 return d.links.filter(l=>l.ticker===ticker&&/^\d{9}$/.test(l.orgNumber)&&Number.isFinite(l.sharePct)&&l.sharePct>0&&l.sharePct<=100&&safe(l.ownershipSource)&&safe(l.identitySource)).map(l=>{
  const match=(d.assetSnapshot.rows||[]).filter(x=>x.orgNumber===l.orgNumber);
  const a=match.length===1?match[0]:null;
  const asset=a&&Array.isArray(a.plantIds)&&new Set(a.plantIds).size===a.plantIds.length&&a.plantIds.every(Number.isInteger)&&Number.isFinite(a.reportedCapacityMW)&&a.reportedCapacityMW>=0&&Number.isInteger(a.capacityRecords)&&a.capacityRecords>0&&a.capacityRecords<=a.plantIds.length?a:null;
  return {...l,asset,sourceDate:d.assetSnapshot.generated,assetSource:d.assetSnapshot.source};
 });
}
function mount(host,d,ticker){
 const rows=select(d,ticker);if(!host||!rows.length)return false;
 const n=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e},link=(t,u)=>{const a=n("a",t,"sw-textlink");a.href=u;a.target="_blank";a.rel="noopener noreferrer";return a};
 host.append(n("h2","Reported corporate ownership & assets"),n("p","Dated ownership evidence. Main-owner asset capacity does not establish current group capacity, equity-adjusted exposure or production.","sw-meta"));
 for(const r of rows){const details=n("details"),summary=n("summary",r.subsidiary+" · "+r.sharePct+"% reported direct ownership");details.append(summary,n("p",r.parent+" → "+r.subsidiary+" · as of "+r.asOf+" · organisation "+r.orgNumber),link("Annual report · "+r.sourceLocator+" ↗",r.ownershipSource),n("p"),link("Brønnøysund legal identity ↗",r.identitySource));
 if(r.asset){const a=r.asset;details.append(n("p",a.plantIds.length+" NVE main-owner plant records · "+a.reportedCapacityMW.toLocaleString("en-GB")+" MW reported nameplate capacity · "+a.zones.join(", ")),n("p","Energy register dated "+r.sourceDate.slice(0,10)+" · "+a.capacityRecords+" capacity records · NVE / NLOD","sw-meta"),link("Energy source snapshot ↗",r.assetSource))}host.append(details)}
 return true;
}
const api={select,mount};if(typeof module==="object"&&module.exports)module.exports=api;else global.StockwatchOwnership=api;
})(typeof window!=="undefined"?window:{});
