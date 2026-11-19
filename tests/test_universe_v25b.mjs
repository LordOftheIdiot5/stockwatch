import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const src=fs.readFileSync(new URL('../v4.js',import.meta.url),'utf8');
const a=src.indexOf('function researchUniverse('),b=src.indexOf('function directoryRows(',a);
const researchUniverse=Function(src.slice(a,b)+'\nreturn researchUniverse')();
const read=p=>JSON.parse(fs.readFileSync(new URL(p,import.meta.url),'utf8'));
test('all curated targets visible without activating scanner prices',()=>{
 const monitored=read('../watchlist.json').tickers;
 const targets=read('../data/research-targets.json');
 const rows=researchUniverse(monitored,targets,null);
 const extra=rows.filter(r=>r.referenceOnly);
 assert.equal(monitored.length,139);
 assert.ok(monitored.some(r=>r.ticker==='NHY.OL'&&r.mic==='XOSL'&&r.isin==='NO0005052605'));
 assert.ok(!extra.some(r=>r.referenceId==='XOSL:NHY'));
 assert.equal(targets.targets.length,75);
 assert.equal(extra.length,74);
 assert.equal(rows.length,213);
 assert.equal(new Set(rows.map(r=>r.ticker)).size,rows.length);
 assert.ok(extra.every(r=>r.unavailable===true&&r.close==null&&r.changePct==null&&r.sector));
});
test('same venue ticker overlap excluded; A and B stay separate',()=>{
 const monitored=[{ticker:'ATCO-A.ST',exchange:'Stockholm'}];
 const targets={targets:[{id:'XSTO:ATCO A',symbol:'ATCO A',name:'Atlas A',mic:'XSTO'},{id:'XSTO:ATCO B',symbol:'ATCO B',name:'Atlas B',mic:'XSTO'}]};
 const rows=researchUniverse(monitored,targets,{records:[{id:'XSTO:ATCO B',symbol:'ATCO B',mic:'XSTO',mappingStatus:'candidate',currentCandidate:{figi:'BBG000BLNNH6'}}]});
 assert.equal(rows.length,2);
 assert.equal(rows[1].figi,'BBG000BLNNH6');
 assert.equal(rows[1].referenceOnly,true);
});
