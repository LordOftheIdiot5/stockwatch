import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const src=fs.readFileSync(new URL('../v4.js',import.meta.url),'utf8');
const a=src.indexOf('function comparisonDate('),b=src.indexOf('function overview()',a);
const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const P=x=>x+'%';
const {coverageHeatRows,coverageHeatmap,referenceCatalogRows,screenFinancialRows}=Function('E','P',src.slice(a,b)+'\nreturn {coverageHeatRows,coverageHeatmap,referenceCatalogRows,screenFinancialRows}')(E,P);
const rows=[{ticker:'A',name:'A',sector:'Industry',close:10,changePct:0,rvol:1,annualVolPct:20},{ticker:'B',name:'B',sector:'Industry',close:20,changePct:-4,rvol:3,annualVolPct:50,thin:true},{ticker:'ref:X:C',referenceId:'X:C',symbol:'C',name:'C',sector:'Industry',referenceOnly:true,unavailable:true},{ticker:'D',name:'D',close:2,changePct:5,rvol:4,annualVolPct:70}];
test('coverage preserves true zero and distinguishes missing data',()=>{
 assert.equal(coverageHeatRows(rows).length,4);
 assert.equal(coverageHeatRows(rows,'all','observed').length,3);
 assert.equal(coverageHeatRows(rows,'all','missing').length,1);
 const html=coverageHeatmap(rows);
 assert.match(html,/class="sw-heat-cell flat"/);
 assert.match(html,/class="sw-heat-cell no-data"/);
 assert.match(html,/research.html\?instrument=X%3AC/);
});
test('filters reject unavailable observations and thin volume',()=>{
 let defaults={move:'',volume:'',volatility:'',signal:false};
 assert.equal(screenFinancialRows(rows,defaults).length,4);
 assert.deepEqual(screenFinancialRows(rows,{...defaults,move:'0'}).map(x=>x.ticker),['A','B','D']);
 assert.deepEqual(screenFinancialRows(rows,{...defaults,move:'4'}).map(x=>x.ticker),['B','D']);
 assert.deepEqual(screenFinancialRows(rows,{...defaults,volume:'2'}).map(x=>x.ticker),['D']);
 assert.deepEqual(screenFinancialRows(rows,{...defaults,volatility:'40'}).map(x=>x.ticker),['B','D']);
 assert.deepEqual(screenFinancialRows(rows,{...defaults,signal:true}).map(x=>x.ticker),['D']);
});
test('reference records remain a separate venue+FIGI catalog',()=>{
 const d=JSON.parse(fs.readFileSync(new URL('../data/instrument-directory.json',import.meta.url),'utf8'));
 const catalog=referenceCatalogRows(d);
 assert.ok(catalog.length>1000);
 assert.equal(catalog.length,new Set(catalog.map(x=>x.ticker)).size);
 assert.ok(catalog.every(x=>x.unavailable&&x.registryOnly&&x.close==null));
});
