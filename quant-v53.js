/* Descriptive quantitative research. No trade recommendation or synthetic prices. */
(function(global){'use strict';
const num=x=>typeof x==='number'&&Number.isFinite(x);
const day=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x;
const url=x=>{try{return new URL(x).protocol==='https:'}catch{return false}};
function series(rows,key='value'){const m=new Map(),bad=new Set();for(const r of rows||[]){if(!r||!day(r.date)||!num(r[key])||r[key]<=0)continue;if(m.has(r.date)&&m.get(r.date)!==r[key])bad.add(r.date);else m.set(r.date,r[key])}return [...m].filter(([d])=>!bad.has(d)).sort(([a],[b])=>a.localeCompare(b)).map(([date,value])=>({date,value}))}
function quantile(a,q){if(!a.length)return null;const s=[...a].sort((x,y)=>x-y),i=(s.length-1)*q,lo=Math.floor(i);return s[lo]+(s[Math.ceil(i)]-s[lo])*(i-lo)}
function summary(rows,min=30){const p=series(rows),x=p.map(r=>r.value),n=x.length;if(!n)return {n:0};const median=quantile(x,.5),mad=quantile(x.map(v=>Math.abs(v-median)),.5),latest=x.at(-1),mean=x.reduce((a,b)=>a+b,0)/n,sd=n>1?Math.sqrt(x.reduce((a,b)=>a+(b-mean)**2,0)/(n-1)):0;return {n,first:p[0].date,last:p.at(-1).date,latest,premium:(latest-1)*100,median:n>=min?median:null,p10:n>=min?quantile(x,.1):null,p90:n>=min?quantile(x,.9):null,robustZ:n>=min&&mad>0?.6744897501960817*(latest-median)/mad:null,z:n>=min&&sd>0?(latest-mean)/sd:null}}
function liquidity(a,b,shares){if(!num(a)||!num(b)||a<=0||b<=0||!num(shares)||shares<=0)return null;return {aPct:100*shares/a,bPct:100*shares/b,limitingPct:100*shares/Math.min(a,b)}}
function align(a,b,rel,fx=null){
 if(!a||!b||!rel||rel.verified!==true||!url(rel.sourceUrl)||a.listingId===b.listingId||rel.a!==a.listingId||rel.b!==b.listingId||!a.isin||!b.isin||!a.mic||!b.mic||!a.currency||!b.currency||typeof a.adjusted!=='boolean'||a.adjusted!==b.adjusted||a.redistributionPermitted!==true||b.redistributionPermitted!==true||a.derivedResearchPermitted!==true||b.derivedResearchPermitted!==true||!url(a.licenseReference)||!url(b.licenseReference))return [];
 if(rel.kind==='cross_listing'){if(a.isin!==b.isin||a.mic===b.mic||rel.sameUnit!==true)return []}
 else if(rel.kind==='share_class'){if(a.isin===b.isin||!rel.issuerId||rel.economicRightsReviewed!==true||rel.sameUnit!==true)return []}
 else return [];
 if(a.currency!==b.currency&&(!fx||fx.base!==a.currency||fx.quote!==b.currency||fx.derivedResearchPermitted!==true||fx.redistributionPermitted!==true||!url(fx.sourceUrl)||!url(fx.licenseReference)))return [];
 const usable=x=>series((x.bars||[]).filter(r=>num(r.volume)&&r.volume>0),'close'),bm=new Map(usable(b).map(r=>[r.date,r.value])),fm=new Map(series(fx?.rates).map(r=>[r.date,r.value]));
 return usable(a).filter(r=>bm.has(r.date)).flatMap(r=>{const f=a.currency===b.currency?1:fm.get(r.date);return num(f)&&f>0?[{date:r.date,value:r.value*f/bm.get(r.date)}]:[]});
}
const api={series,summary,liquidity,align};if(typeof module==='object'&&module.exports)module.exports=api;else global.StockwatchQuant=api;
})(typeof window!=='undefined'?window:{});
