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

test('individual A/B return renders in both display maps but never strict counts',()=>{
 const pair={ticker:'ref:XCSE:MAERSK A',referenceOnly:true,unavailable:true,sector:'Shipping',name:'Maersk',pairQuote:{close:101,currency:'DKK',date:day,dailyMove:{date:day,previousDate:'2026-11-16',changePct:1.25,method:'individual_daily_closes'}}};
 const rows=reportedMapRows([pair],day);
 for(const render of [coverageHeatmap,compactScreenerHeatmap]){
  const h=render(rows,day,true);assert.match(h,/1.25% · 2026-11-17/);assert.match(h,/A\/B daily move/);assert.doesNotMatch(h,/sw-heat-cell positive/);
  assert.doesNotMatch(render(rows,day,false),/1.25%/);
  assert.doesNotMatch(render(rows,'2026-11-16',true),/1.25%/);
 }
});

test('saved positive-volume move remains distinct from recent zero-volume price',()=>{
 const r={ticker:'TEST',name:'Test',currency:'NOK',sector:'Other',date:day,close:22,volume:0,changePct:0,lastValidMovement:{ticker:'TEST',name:'Test',currency:'NOK',date:'2026-11-16',close:21,volume:100,changePct:5}};
 const rows=reportedMapRows([r],day);
 for(const render of [coverageHeatmap,compactScreenerHeatmap]){
  const html=render(rows,day,true);assert.match(html,/5% · 2026-11-16/);assert.match(html,/21 NOK · saved movement/);assert.match(html,/22 NOK · latest price 2026-11-17/);assert.doesNotMatch(html,/sw-heat-cell positive/);
  assert.doesNotMatch(render(rows,day,false),/saved movement/);
  assert.doesNotMatch(render(reportedMapRows([{...r,lastValidMovement:{...r.lastValidMovement,currency:'EUR'}}],day),day,true),/saved movement/);
 }
});
