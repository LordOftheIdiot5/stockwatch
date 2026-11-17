import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
const src=fs.readFileSync(new URL('../v4.js',import.meta.url),'utf8');
const a=src.indexOf('function comparisonDate('),b=src.indexOf('function overview()',a);
const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const P=x=>x+'%';
const {coverageHeatRows,coverageHeatmap,referenceCatalogRows,screenFinancialRows,latestBroadReportedSession,marketHeatData}=Function('E','P',src.slice(a,b)+'\nreturn {coverageHeatRows,coverageHeatmap,referenceCatalogRows,screenFinancialRows,latestBroadReportedSession,marketHeatData}')(E,P);
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

test('dated last-known prices remain visible without current-session change',()=>{const old={ticker:'A',name:'A',sector:'Industry',close:12.5,currency:'NOK',date:'2026-11-13',marketQuality:'older',changePct:7};assert.equal(coverageHeatRows([old,rows[2]],'all','priced').length,1);const h=coverageHeatmap([old]);assert.match(h,/12\.5 NOK · 2026-11-13/);assert.match(h,/no-data/);assert.doesNotMatch(h,/sw-heat-cell positive/)});

test('V62: latest broadly reported day includes retained valid changes but excludes future or zero-volume rows',()=>{
 const a={ticker:'A',date:'2026-11-17',close:12,currency:'NOK',changePct:1,volume:10};
 const b={...a,ticker:'B'},older={...a,ticker:'C',date:'2026-11-16'};
 const set=[a,b,older,{...a,ticker:'D',date:'2026-11-18'},{...a,ticker:'E',priceStatus:'retained'},{...a,ticker:'F',volume:0},{...a,ticker:'G',referenceOnly:true}];
 const reported=latestBroadReportedSession(set,'2026-11-17T19:42:00Z',2);
 assert.equal(reported.day,'2026-11-17');assert.deepEqual(reported.rows.map(x=>x.ticker),['A','B','E']);
 assert.equal(latestBroadReportedSession(set,'invalid',2),null);
 assert.match(coverageHeatmap(reported.rows),/company.html\?ticker=A/);
 assert.equal(marketHeatData([{...a,referenceOnly:true}]).length,0);
});
test('V61 inventory command returns balanced coverage counts without mutating inputs',()=>{
 const out=JSON.parse(execFileSync(process.execPath,[new URL('../scripts/audit_price_inventory.cjs',import.meta.url).pathname],{encoding:'utf8'}));
 assert.equal(out.total,out.records.length);
 assert.equal(Object.values(out.counts).reduce((a,b)=>a+b,0),out.total);
 assert.equal(Object.values(out.byVenue).reduce((a,b)=>a+b.total,0),out.total);
 assert.ok(out.counts.scanner>0);assert.ok(out.records.every(r=>r.id&&r.status));
});

test('V63: issuer operating data keeps dated source, units and reporting scopes separate',()=>{
 const start=src.indexOf('function companyOperatingRows('),end=src.indexOf('function companyOperatingHTML(',start);
 const operating=Function(src.slice(start,end)+'\nreturn companyOperatingRows')();
 const d=JSON.parse(fs.readFileSync(new URL('../data/company-operating-metrics.json',import.meta.url),'utf8'));
 const all=operating(d);
 assert.equal(all.length,2);
 assert.ok(all.reduce((n,c)=>n+c.series.reduce((m,v)=>m+v.observations.length,0),0)>=82);
 const w=operating(d,'WAWI.OL')[0].series.find(v=>v.key==='net_freight');
 const h=operating(d,'HAUTO.OL')[0].series.find(v=>v.key==='net_freight');
 assert.deepEqual([w.frequency,w.observations.at(-1).value,h.frequency,h.observations.at(-1).value],['quarterly',64.4,'monthly',81.8]);
 assert.deepEqual(operating(d,'WWI.OL'),[]); // related issuer, not the same security.
 const bad=structuredClone(d);bad.companies[0].series[0].observations.at(-1).sourceUrl='https://example.com/';
 assert.equal(operating(bad,'WAWI.OL')[0].series[0].observations.length,2);
 assert.deepEqual(operating({...d,compiledOn:'invalid'}),[]);
});

test('V64: dated ownership and quarter-end profit stay separate; no name-based mappings',()=>{
 const start=src.indexOf('function reportedInvestments('),end=src.indexOf('function investmentHTML(',start);
 const parse=Function(src.slice(start,end)+'\nreturn reportedInvestments')();
 const data=JSON.parse(fs.readFileSync(new URL('../data/issuer-investments.json',import.meta.url),'utf8'));
 const all=parse(data);assert.equal(all.length,6);
 const w=all.find(r=>r.targetId==='wallenius-wilhelmsen');
 assert.deepEqual(w.ownership.map(p=>[p.asOf,p.percent]),[['2026-09-30',37.9],['2026-10',37.04]]);
 assert.equal(w.profitContribution.at(-1).usdMillion,72);
 assert.equal(w.bookValue.periodEnd,'2026-09-30');
 assert.deepEqual(w.ownerTickers,['WWI.OL','WWIB.OL']);
 const h=all.find(r=>r.targetId==='hyundai-glovis');assert.equal(h.targetTicker,null);assert.equal(h.profitContribution.at(-1).usdMillion,51);
 const bad=structuredClone(data);bad.owners[0].investments[0].targetTicker='HAUTO.OL';
 assert.equal(parse(bad).length,5);
 const wrongSource=structuredClone(data);wrongSource.owners[0].investments[0].ownership[1].sourceUrl='https://example.com/';
 assert.equal(parse(wrongSource)[0].ownership.length,1);
 assert.deepEqual(parse(null),[]);
});

test('V65: official Ro-Ro history preserves quarter, country, unit, missing periods and real zero',()=>{
 const start=src.indexOf('function roroTrafficRows('),end=src.indexOf('function roroMarketHTML(',start);
 const parse=Function(src.slice(start,end)+'\nreturn roroTrafficRows')();
 const data=JSON.parse(fs.readFileSync(new URL('../data/shipping-roro-traffic.json',import.meta.url),'utf8'));
 const rows=parse(data);assert.equal(rows.length,10);
 assert.ok(rows.reduce((n,r)=>n+r.history.length,0)>=175);
 const eu=rows.find(r=>r.countryCode==='EU27_2020');assert.ok(eu.period>='2026-Q1');assert.equal(eu.history.find(p=>p.period==='2026-Q1').date,'2026-03-31');
 assert.ok(rows.every(r=>r.unit==='thousand tonnes'&&r.frequency==='quarterly'));
 const fixture=structuredClone(data);fixture.series[0].history=[{period:'2025-Q1',value:0},{period:'2025-Q3',value:9},{period:'2025-Q4',value:null}];
 const first=parse(fixture)[0];assert.equal(first.history[0].value,0);assert.equal(first.history.length,2);
 assert.deepEqual(parse({...data,provider:'unknown'}),[]);
});

test('V66: freight analysis uses exact dated licensed closes and never bridges missing periods',()=>{
 const start=src.indexOf('function freightPeriodAnalysis('),end=src.indexOf('function freightAnalysisHTML(',start);
 const analyse=Function(src.slice(start,end)+'\nreturn freightPeriodAnalysis')();
 const series={frequency:'monthly',observations:[
 {periodEnd:'2026-06-30',publishedOn:'2026-07-10',value:80},
 {periodEnd:'2026-07-31',publishedOn:'2026-08-10',value:84},
 {periodEnd:'2026-09-30',publishedOn:'2026-10-10',value:90}
 ]};
 const history={ticker:'WAWI.OL',redistributionPermitted:true,source:'fixture',sourceUrl:'https://example.com',licenseReference:'fixture permission',currency:'NOK',adjusted:false,bars:[{date:'2026-06-30',close:100},{date:'2026-07-30',close:110},{date:'2026-08-01',close:999},{date:'2026-09-20',close:120}]};
 const x=analyse(series,history,'WAWI.OL');
 assert.equal(x.pairs.length,1);assert.ok(Math.abs(x.pairs[0].x-5)<1e-9);assert.ok(Math.abs(x.pairs[0].y-10)<1e-9);
 assert.equal(x.rows[1].stock.date,'2026-07-30');assert.equal(x.rows[2].stock,null);assert.equal(x.rows[2].rateChange,null);assert.equal(x.correlation,null);
 for(const h of [null,{...history,redistributionPermitted:false},{...history,ticker:'WWI.OL'}]){const y=analyse(series,h,'WAWI.OL');assert.equal(y.licensed,false);assert.equal(y.pairs.length,0);assert.equal(y.rows.length,3)}
});
test('V66: correlation requires twelve consecutive paired changes and nonconstant series',()=>{
 const start=src.indexOf('function freightPeriodAnalysis('),end=src.indexOf('function freightAnalysisHTML(',start);
 const analyse=Function(src.slice(start,end)+'\nreturn freightPeriodAnalysis')();
 const observations=[],bars=[];let rate=80,price=100;
 for(let i=0;i<13;i++){const date=new Date(Date.UTC(2025,i+1,0)).toISOString().slice(0,10);rate*=1+i/100;price*=1+i/50;observations.push({periodEnd:date,publishedOn:date,value:rate});bars.push({date,close:price})}
 const series={frequency:'monthly',observations};
 const history={ticker:'TEST',redistributionPermitted:true,source:'fixture',sourceUrl:'https://example.com',licenseReference:'fixture',currency:'NOK',adjusted:false,bars};
 const x=analyse(series,history,'TEST');assert.equal(x.pairs.length,12);assert.ok(Math.abs(x.correlation-1)<1e-9);
 assert.equal(analyse({...series,observations:observations.slice(0,12)},history,'TEST').correlation,null);
 assert.equal(analyse(series,{...history,bars:bars.map(b=>({...b,close:100}))},'TEST').correlation,null);
});

test('V67: same-period freight-volume scenarios separate proxy and hypothetical costs',()=>{
 const start=src.indexOf('function freightScenario('),end=src.indexOf('function freightScenarioHTML(',start);
 const {freightScenario,freightScenarioBaseline}=Function(src.slice(start,end)+'\nreturn {freightScenario,freightScenarioBaseline}')();
 const d=JSON.parse(fs.readFileSync(new URL('../data/company-operating-metrics.json',import.meta.url),'utf8'));
 const b=freightScenarioBaseline(d.companies.find(x=>x.ticker==='WAWI.OL'));
 assert.equal(b.rate,64.4);assert.equal(b.volume,13.2);assert.equal(b.periodEnd,'2026-09-30');
 const x=freightScenario(b.rate,b.volume,10,0,15);
 assert.ok(Math.abs(x.baseline-850.08)<1e-8);assert.ok(Math.abs(x.delta-85.008)<1e-8);assert.ok(Math.abs(x.illustrativeContribution-70.008)<1e-8);
 assert.equal(freightScenario(64.4,13.2,-101,0,0),null);assert.equal(freightScenario(64.4,13.2,NaN,0,0),null);
 assert.equal(freightScenario(64.4,13.2,-100,0,0).scenario,0);
 const wrong=structuredClone(d.companies[0]);wrong.series.find(s=>s.key==='transport_volume').unit='tonnes';assert.equal(freightScenarioBaseline(wrong),null);
});

test('V68: reported-map date is separate from strict filters; retained and pair prices stay neutral',()=>{
 const start=src.indexOf('function comparisonDate('),end=src.indexOf('function overview()',start);
 const {screenerHeatRows,compactScreenerHeatmap}=Function('E','P','N',src.slice(start,end)+'\nreturn {screenerHeatRows,compactScreenerHeatmap}')(E,P,x=>String(x));
 const row={ticker:'WAWI.OL',name:'WAWI',sector:'Shipping',date:'2026-11-17',currency:'NOK',close:166.7,changePct:0.85,volume:100,priceStatus:'reported'};
 const data=[row,{...row,ticker:'retained',priceStatus:'retained'},{...row,ticker:'older',date:'2026-11-16'},{...row,ticker:'pair',referenceOnly:true,pairQuote:{close:10,date:'2026-11-17',currency:'NOK'}}];
 const result=screenerHeatRows(data,'2026-11-17','2026-11-16');
 assert.deepEqual(result.map(x=>x.marketQuality),['observed','unconfirmed','older','unavailable']);
 const html=compactScreenerHeatmap(result);assert.match(html,/sw-compact-heatgrid/);assert.equal((html.match(/sw-compact-heatsector /g)||[]).length,1);assert.equal((html.match(/class="sw-heat-cell positive"/g)||[]).length,1);
 assert.ok(screenerHeatRows(data,'2026-11-17','2026-11-16','missing').every(x=>x.marketQuality==='unavailable'));
 assert.equal(screenerHeatRows([row],'2026-11-17','2026-11-16','comparable')[0].marketQuality,'unconfirmed');
});

test('V73: complete 16-month HAUTO operating history and narrowly scoped exchange notice sources',()=>{
 const start=src.indexOf('function companyOperatingRows('),end=src.indexOf('function freightPeriodAnalysis(',start);
 const operating=Function(src.slice(start,end)+'\nreturn companyOperatingRows')();
 const data=JSON.parse(fs.readFileSync(new URL('../data/company-operating-metrics.json',import.meta.url),'utf8'));
 const ha=operating(data,'HAUTO.OL')[0];
 for(const series of ha.series){
  const dates=series.observations.map(p=>p.periodEnd);
  for(let i=0;i<16;i++){
   const date=new Date(Date.UTC(2025,7+i,0)).toISOString().slice(0,10);
   assert.ok(dates.includes(date),series.key+' missing '+date);
  }
 }
 const h=ha.series.find(v=>v.key==='net_freight');
 assert.equal(h.observations.find(p=>p.periodEnd==='2026-01-31').value,77.7);
 assert.equal(h.observations.find(p=>p.periodEnd==='2026-02-28').value,80.7);
 const bad=structuredClone(data),series=bad.companies.find(c=>c.ticker==='HAUTO.OL').series[0];
 series.observations.find(p=>p.periodEnd==='2026-01-31').sourceUrl='https://live.euronext.com/en/products/equities/company-news/2026-02-06-unrelated-issuer';
 assert.equal(operating(bad,'HAUTO.OL')[0].series[0].observations.some(p=>p.periodEnd==='2026-01-31'),false);
});
