import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const s=fs.readFileSync(new URL('../v4.js',import.meta.url),'utf8');
const body=s.slice(s.indexOf('function comparisonDate('),s.indexOf('function overview()'));
const {olderMapChange,neutralMapDetail,coverageHeatmap,compactScreenerHeatmap,reportedMapRows}=Function('E','P','N',body+'\nreturn {olderMapChange,neutralMapDetail,coverageHeatmap,compactScreenerHeatmap,reportedMapRows}')(String,x=>String(x)+'%',String);
const day='2026-11-17',old={ticker:'TEST',name:'Test',sector:'Other',date:'2026-11-16',currency:'NOK',close:21,volume:100,changePct:5,priceStatus:'retained'};
test('older movements visible as separately dated neutral tiles, not current-session colors',()=>{
 const rows=reportedMapRows([old],day);
 for(const html of [coverageHeatmap(rows,day,true),compactScreenerHeatmap(rows,day,true)]){
  assert.match(html,/5% · 2026-11-16/);
  assert.match(html,/earlier session/);
  assert.doesNotMatch(html,/sw-heat-cell positive/);
 }
 assert.doesNotMatch(coverageHeatmap(rows,day,false),/earlier session/);
});
test('invalid dates, same session, zero volume and reference prices never gain older changes',()=>{
 for(const row of [{...old,volume:0},{...old,date:day},{...old,date:'2026-02-30'},{...old,referenceOnly:true},{...old,changePct:null},{...old,date:'2026-11-18'}])assert.equal(olderMapChange(row,day),null);
 assert.match(neutralMapDetail({...old,volume:0},day,true),/No trading volume/);
 assert.match(neutralMapDetail({referenceOnly:true,pairQuote:{close:20,date:day,currency:'SEK'}},day,true),/A\/B price only/);
});
