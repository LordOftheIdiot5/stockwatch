import test from 'node:test';
import assert from 'node:assert/strict';
import {buildMaritimePulse,asPercent,valuePercent} from '../scripts/maritime-pulse-v121.mjs';

const NOW=new Date('2026-11-23T21:00:00Z');
const official='https://source.example.gov/official';
const makeHistory=(a,b,form='date')=>[{[form]:a[0],value:a[1]},{[form]:b[0],value:b[1]}];
const yearHistory=(a,b)=>makeHistory([a+'-12-31',853611611],[b+'-12-31',913279048]);
const oneSeries=(key,period,unit,history)=>({key,period,unit,history,sourceUrl:official});
const data={
 freight:{generated:'2026-11-23T15:29:36Z',series:[
  oneSeries('usda:gulf-japan-index','2026-11-18','index, 2017 = 100',makeHistory(['2026-11-11',185.61],['2026-11-18',184.97])),
  oneSeries('usda:pnw-japan-index','2026-11-18','index, 2017 = 100',makeHistory(['2026-11-11',187.65],['2026-11-18',187.65]))
 ]},
 connectivity:{generated:'2026-11-23T15:29:39Z',source:{sourceUrl:official},series:[
  oneSeries('unctad:lsci-monthly:denmark','2026-09','index',makeHistory(['2026-08-01',86.93735],['2026-09-01',81.59456])),
  oneSeries('unctad:lsci-monthly:sweden','2026-09','index',makeHistory(['2026-08-01',109.9681],['2026-09-01',105.94177])),
  oneSeries('unctad:lsci-monthly:norway','2026-09','index',makeHistory(['2026-08-01',55.28495],['2026-09-01',56.45433]))
 ]},
 roro:{observedOn:'2026-11-23',sourceUrl:official,series:[
  {countryCode:'NO',period:'2026-Q2',unit:'thousand tonnes',history:makeHistory(['2025-Q2',1094],['2026-Q2',1161],'period')},
  {countryCode:'SE',period:'2026-Q2',unit:'thousand tonnes',history:makeHistory(['2025-Q2',11761],['2026-Q2',12166],'period')},
  {countryCode:'NL',period:'2026-Q2',unit:'thousand tonnes',history:makeHistory(['2025-Q2',6806],['2026-Q2',6856],'period')}
 ]},
 ports:{generated:'2026-11-23T15:29:38Z',source:{sourceUrl:official},series:[
  oneSeries('worldbank:container-port-teu:WLD','2024','TEU',yearHistory(2023,2024)),
  oneSeries('worldbank:container-port-teu:VNM','2024','TEU',makeHistory(['2023-12-31',21069746],['2024-12-31',24423183])),
  oneSeries('worldbank:container-port-teu:NOR','2024','TEU',makeHistory(['2023-12-31',882560],['2024-12-31',862983]))
 ]},
 company:{compiledOn:'2026-11-17',companies:[{ticker:'WAWI.OL',series:[
  {key:'net_freight',unit:'USD/m³',observations:[
   {periodEnd:'2026-06-30',value:61.4,sourceUrl:official},{periodEnd:'2026-09-30',value:64.4,sourceUrl:official}]},
  {key:'transport_volume',unit:'million m³',observations:[
   {periodEnd:'2026-06-30',value:13.6,sourceUrl:official},{periodEnd:'2026-09-30',value:13.2,sourceUrl:official}]},
  {key:'backlog',unit:'USD billion',observations:[
   {periodEnd:'2026-06-30',value:6.5,sourceUrl:official},{periodEnd:'2026-09-30',value:5.8,sourceUrl:official}]}
 ]}]},
 rates:{reportedAt:'2026-11-19',isBrokerRate:false,sourceUrl:official,rates:[
  {id:'us-gulf-japan-grain-2026-11-12',value:72.75,observationDate:'2026-11-12'},
  {id:'pnw-japan-grain-2026-11-12',value:39.5,observationDate:'2026-11-12'}
 ]}
};
const clone=x=>JSON.parse(JSON.stringify(x));
test('six source-dated indicators from compatible real-report-shaped data',()=>{
 const r=buildMaritimePulse(data,{now:NOW});
 assert.equal(r.status,'source_backed');assert.equal(r.signalCount,6,JSON.stringify({ids:r.signals.map(x=>x.id),missing:r.missing}));
 assert.deepEqual(r.signals.map(x=>x.id),[
  'usda-grain-week','nordic-liner-network','nordic-roro-yoy',
  'global-container-history','wallenius-operations','usda-grain-indications'
 ]);
 assert.deepEqual(r.signals[0].figures.map(x=>x.changePct),[-0.3,0]);
 assert.deepEqual(r.signals[1].figures.map(x=>x.changePct),[-6.1,-3.7,2.1]);
 assert.deepEqual(r.signals[2].figures.map(x=>x.changePct),[6.1,3.4,0.7]);
 assert.deepEqual(r.signals[3].figures.map(x=>x.changePct),[7,15.9,-2.2]);
 assert.deepEqual(r.signals[4].figures.map(x=>x.changePct),[4.9,-2.9,-10.8]);
 assert.equal(r.signals[5].kind,'observed_levels');
 assert.deepEqual(r.signals[5].figures.map(x=>x.value),[72.75,39.5]);
});
test('carry original units, periods, scope and links; never invent a daily market',()=>{
 const r=buildMaritimePulse(data,{now:NOW});
 for(const x of r.signals){
  assert.match(x.sourceUrl,/https:/);
  assert.ok(x.period);
  assert.ok(x.caveat.includes('not ')||x.caveat.includes('Not ')||x.caveat.includes('Country totals'));
  assert.notEqual(x.kind,'forecast');assert.equal(x.priceTarget,undefined);
  assert.equal(x.cause,undefined);assert.equal(x.liveAIS,undefined);
 }
 assert.equal(r.signals[3].historical,true);
 assert.equal(r.signals[4].figures[0].unit,'USD/m³');
 assert.match(r.signals[5].caveat,/different origins/);
});
test('mixed-frequency, quarter mismatch and source-date gap fail closed',()=>{
 const d=clone(data);
 d.roro.series[1].period='2026-Q1';
 d.connectivity.series[1].period='2026-08';
 d.freight.series[0].history[0].date='2026-11-10';
 const r=buildMaritimePulse(d,{now:NOW});
 assert.ok(!r.signals.some(x=>x.id==='nordic-roro-yoy'));
 assert.ok(!r.signals.some(x=>x.id==='nordic-liner-network'));
 assert.ok(!r.signals.some(x=>x.id==='usda-grain-week'));
 assert.ok(r.missing.includes('eurostat_roro_yoy_unavailable'));
});
test('absence is not converted to zero or a phantom growth observation',()=>{
 const d=clone(data);
 d.ports.series[0].history.at(-1).value=null;
 d.company.companies[0].series[0].observations.at(-1).value=null;
 d.rates.rates=[];
 const r=buildMaritimePulse(d,{now:NOW});
 assert.ok(!r.signals.some(x=>x.id==='global-container-history'));
 assert.ok(!r.signals.some(x=>x.id==='wallenius-operations'));
 assert.ok(!r.signals.some(x=>x.id==='usda-grain-indications'));
 assert.equal(asPercent(10,0),null);assert.equal(asPercent(NaN,10),null);
});
test('stale readings do not claim to be current signals',()=>{
 const r=buildMaritimePulse(data,{now:new Date('2031-11-23T21:00:00Z')});
 assert.equal(r.signalCount,0);assert.equal(r.status,'no_verified_comparisons');
});
test('broker-rate or untrusted source cannot enter public source-backed output',()=>{
 const d=clone(data);
 d.rates.isBrokerRate=true;
 d.connectivity.source.sourceUrl='http://unverified.example/not-https';
 const r=buildMaritimePulse(d,{now:NOW});
 assert.ok(!r.signals.some(x=>x.id==='usda-grain-indications'));
 assert.ok(!r.signals.some(x=>x.id==='nordic-liner-network'));
});
test('pure output, same snapshot produces same evidence without altering input',()=>{
 const original=JSON.stringify(data);
 const a=buildMaritimePulse(data,{now:NOW});
 const b=buildMaritimePulse(data,{now:NOW});
 assert.deepEqual(a,b);assert.equal(JSON.stringify(data),original);
 assert.equal(valuePercent(0),'0.0%');assert.equal(valuePercent(-4.89),'-4.9%');
});
test('invalid time and non-numeric values are rejected',()=>{
 assert.throws(()=>buildMaritimePulse(data,{now:new Date('invalid')}),/invalid_pulse_clock/);
 const d=clone(data);d.freight.series[0].history.at(-1).value='184.97';
 const r=buildMaritimePulse(d,{now:NOW});
 assert.ok(!r.signals.some(x=>x.id==='usda-grain-week'));
});
