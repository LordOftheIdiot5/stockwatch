import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const read=p=>JSON.parse(fs.readFileSync(new URL('../'+p,import.meta.url),'utf8'));
const source=fs.readFileSync(new URL('../v4.js',import.meta.url),'utf8');
const extract=(a,b)=>source.slice(source.indexOf(a),source.indexOf(b,source.indexOf(a)));
const registry=Function(extract('function referenceCatalogRows(','function screenMetric(')+'\nreturn referenceCatalogRows')();
const quick=Function(extract('function quickMatches(','function wireQuickSearch(')+'\nreturn quickMatches')();
test('500 listing target preserves scanner and existing curated records',()=>{
 const d=read('data/research-expansion.json'),w=read('watchlist.json').tickers,t=read('data/research-targets.json').targets;
 const catalog=read('data/instrument-directory.json').records,keys=new Set(catalog.map(x=>x.mic+':'+x.figi));
 const selected=registry(d);
 assert.equal(w.length,138);assert.equal(t.length,75);assert.equal(selected.length,287);assert.equal(w.length+t.length+selected.length,500);
 assert.equal(new Set(d.records.map(x=>x.shareClassFIGI)).size,287);
 assert.ok(d.records.every(x=>keys.has(x.mic+':'+x.figi)&&x.quoteStatus==='not_connected'&&x.sourceObservedAt));
 assert.ok(selected.every(x=>x.unavailable&&x.referenceOnly&&x.close==null));
 const known=[...read('data/registered-source-status.json').figiCandidates,...read('data/research-coverage.json').records.flatMap(x=>[x.currentCandidate,x.lastCandidate]).filter(Boolean)];
 const shares=new Set(known.map(x=>x.shareClassFIGI).filter(Boolean));
 assert.ok(d.records.every(x=>!shares.has(x.shareClassFIGI)));
});
test('direct search ranks exact symbols and identifiers first',()=>{
 const rows=[{ticker:'AAA.OL',name:'Alpha'},{ticker:'ref:A',symbol:'AAA',name:'Other',referenceOnly:true,figi:'BBG000TEST01'},{ticker:'B',name:'Alpha Beta'}];
 assert.equal(quick(rows,'AAA')[0].ticker,'ref:A');
 assert.equal(quick(rows,'Alpha')[0].ticker,'AAA.OL');
 assert.equal(quick(rows,'BBG000TEST01')[0].ticker,'ref:A');
 assert.deepEqual(quick(rows,'  '),[]);
});
