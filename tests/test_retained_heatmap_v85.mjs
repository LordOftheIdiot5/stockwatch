import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),S=require('../screener-v51.js');
const js=fs.readFileSync(new URL('../v4.js',import.meta.url),'utf8');
const a=js.indexOf('function comparisonDate('),b=js.indexOf('function overview()',a);
const {reportedMapRows,latestBroadReportedSession,latestBroadSession,observationQuality,marketHeatData,screenerHeatRows}=Function(js.slice(a,b)+'\nreturn {reportedMapRows,latestBroadReportedSession,latestBroadSession,observationQuality,marketHeatData,screenerHeatRows}')();
const day='2026-11-17',stamp=day+'T23:27:35Z';
const base={ticker:'A',date:day,close:12,currency:'NOK',volume:100,changePct:-2,priceStatus:'retained'};
test('full failure retains maps, never generates fresh signals',()=>{
 const rows=Array.from({length:20},(_,i)=>({...base,ticker:'TEST'+i,changePct:i%3-1}));
 const report=latestBroadReportedSession(rows,stamp);
 assert.equal(report.day,day);assert.equal(report.rows.length,20);
 assert.equal(marketHeatData(reportedMapRows(rows,day)).length,20);
 assert.equal(marketHeatData(screenerHeatRows(rows,day,day)).length,20);
 assert.equal(marketHeatData(screenerHeatRows(rows,day,day,'comparable')).length,0);
 assert.equal(latestBroadSession(rows,'2026-11-18'),null);
 assert.ok(rows.every(r=>observationQuality(r,day)==='unconfirmed'&&!S.comparable(r,day)));
 assert.ok(report.rows.every(r=>r.priceStatus==='retained'));
});
test('no fabricated movement, no date mixing, no reference substitutions',()=>{
 const invalid=[{...base,ticker:'B',volume:0},{...base,ticker:'C',changePct:null},{...base,ticker:'D',date:'2026-11-16'},{...base,ticker:'E',referenceOnly:true},{...base,ticker:'F',currency:null},{...base,ticker:'G',unavailable:true},{...base,ticker:'H',date:'2026-11-18'}];
 assert.deepEqual(marketHeatData(reportedMapRows([base,...invalid],day)).map(x=>x.ticker),['A']);
 assert.equal(marketHeatData(reportedMapRows([{...base,date:'2026-11-31'}],'2026-11-31')).length,0);
});
test('saved production snapshot has same display coverage in both maps',()=>{
 const data=JSON.parse(fs.readFileSync(new URL('../data/signals.json',import.meta.url),'utf8'));
 const report=latestBroadReportedSession(data.companies,data.generated);
 assert.ok(report&&report.rows.length>=10);
 const expected=data.companies.filter(r=>r.date===report.day&&!r.referenceOnly&&!r.unavailable&&r.close>0&&Number.isFinite(r.changePct)&&r.volume>0&&r.currency);
 assert.equal(marketHeatData(reportedMapRows(data.companies,report.day)).length,expected.length);
 assert.equal(marketHeatData(screenerHeatRows(data.companies,report.day,report.day)).length,expected.length);
 assert.equal(report.rows.length,expected.length);
});
