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

test('V62: latest broadly reported day is bounded by snapshot and excludes retained or zero volume rows',()=>{
 const a={ticker:'A',date:'2026-11-17',close:12,currency:'NOK',changePct:1,volume:10};
 const b={...a,ticker:'B'},older={...a,ticker:'C',date:'2026-11-16'};
 const set=[a,b,older,{...a,ticker:'D',date:'2026-11-18'},{...a,ticker:'E',priceStatus:'retained'},{...a,ticker:'F',volume:0},{...a,ticker:'G',referenceOnly:true}];
 const reported=latestBroadReportedSession(set,'2026-11-17T19:42:00Z',2);
 assert.equal(reported.day,'2026-11-17');assert.deepEqual(reported.rows.map(x=>x.ticker),['A','B']);
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
 assert.equal(all.reduce((n,c)=>n+c.series.reduce((m,v)=>m+v.observations.length,0),0),38);
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
