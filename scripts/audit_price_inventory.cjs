/* V61 read-only inventory of the curated universe. Run: node scripts/audit_price_inventory.cjs
   Emits JSON to stdout; does not publish new prices, call vendors or modify datasets. */
'use strict';
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const read=f=>JSON.parse(fs.readFileSync(path.join(root,f),'utf8'));
const S=require('../screener-v51.js');
const src=fs.readFileSync(path.join(root,'v4.js'),'utf8');
function extract(name,next){
 const a=src.indexOf('function '+name+'('),b=src.indexOf(next,a);
 if(a<0||b<=a)throw Error('UI function not found: '+name);
 return Function(src.slice(a,b)+'\nreturn '+name)();
}
const universe=extract('researchUniverse','/* V26:');
const registry=extract('referenceCatalogRows','function screenMetric(');
const licensedRows=extract('licensedReferenceRows','function licensedReferenceCount(');
const signals=read('data/signals.json'),context=read('data/context.json');
const live=new Map(signals.companies.map(r=>[r.ticker,r]));
const monitored=read('watchlist.json').tickers.map(w=>live.has(w.ticker)?{...w,...live.get(w.ticker)}:{...w,unavailable:true});
const base=universe(monitored,read('data/research-targets.json'),read('data/research-coverage.json'));
const rows=[...base,...registry(read('data/research-expansion.json')).map(r=>({...r,expandedReference:true}))];
const licensed=licensedRows(read('data/licensed-price-coverage.json'),rows);
const covered=new Set(),byVenue={},records=[];
for(const r of rows){
 const pair=S.pairQuote(r,context.shareClasses);
 const q=S.hasPrice(r)?r:licensed.get(r.ticker)||pair;
 const status=S.hasPrice(r)?'scanner':licensed.has(r.ticker)?'licensed_eod':pair?'pair_observation':'missing';
 if(status==='scanner')covered.add(r.ticker);if(pair)covered.add(pair.ticker);
 const venue=r.exchange||r.mic||'Unknown';
 const v=byVenue[venue]||={total:0,scanner:0,licensed_eod:0,pair_observation:0,missing:0};
 v.total++;v[status]++;
 records.push({id:r.ticker,name:r.name,venue,mic:r.mic||null,isin:r.isin||null,figi:r.figi||null,status,date:q?.date||q?.lastDate||null});
}
const unmatchedPairLegs=(context.shareClasses||[]).flatMap(p=>[p.a,p.b]).filter(t=>!covered.has(t));
const counts=Object.fromEntries(['scanner','licensed_eod','pair_observation','missing'].map(k=>[k,records.filter(r=>r.status===k).length]));
console.log(JSON.stringify({snapshot:signals.generated,total:rows.length,counts,byVenue,unmatchedPairLegs,historyCoverage:read('data/history-coverage.json'),records},null,2));
