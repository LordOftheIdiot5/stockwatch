import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const r=JSON.parse(readFileSync('data/shipping-roro-traffic.json','utf8'));
const p=JSON.parse(readFileSync('data/shipping-ports.json','utf8'));
const html=readFileSync('shipping.html','utf8');
const regional=readFileSync('shipping-regional-v117t.js','utf8');
const economics=readFileSync('shipping-offshore-econ-v117t.js','utf8');
const sandbox={};
runInNewContext(economics,sandbox);
const calc=sandbox.StockwatchOSVEconomics.compute;
test('Existing official Norway/EU quarterly series are dated, rights labelled and genuinely numeric',()=>{
 assert.equal(r.schemaVersion,1);assert.equal(r.provider,'Eurostat');assert.equal(r.datasetCode,'mar_go_qmc');
 assert.ok(r.sourceUrl.includes('ec.europa.eu'));assert.ok(r.licenseUrl.includes('ec.europa.eu'));
 const byCode=Object.fromEntries(r.series.map(x=>[x.countryCode,x]));
 for(const [code,period,value] of [['NO','2026-Q2',1161],['SE','2026-Q2',12166],['DK','2026-Q2',6041],['EU27_2020','2026-Q1',100229]]){
  const x=byCode[code];assert.ok(x);
  assert.equal(x.period,period);assert.equal(x.value,value);assert.equal(x.unit,'thousand tonnes');
  assert.equal(x.frequency,'quarterly');assert.ok(x.history.length>=3);
 }
});
test('Norwegian container traffic comes from attributed annual World Bank series, not a charter rate',()=>{
 assert.equal(p.source.sourceUrl,'https://data.worldbank.org/indicator/IS.SHP.GOOD.TU');
 const no=p.series.find(x=>x.countryCode==='NOR');assert.ok(no);
 assert.equal(no.value,862983);assert.equal(no.period,'2024');assert.equal(no.unit,'TEU');assert.equal(no.frequency,'annual');
 assert.equal(no.isActualRate,false);
 assert.ok(regional.includes('EU27_2020')&&regional.includes('NO'));
 assert.ok(regional.includes('Kystdatahuset')||regional.includes('Kystverket'));
 assert.ok(html.includes('shipping-regional-v117t.js?v=117t1'));
});
test('Original NavProfit-style charter contribution is derived solely from user assumptions and actual rate basis',()=>{
 const input={rate:34153,serviceDays:30,billableDays:25,transitDays:3,dailyOpex:12000,fuelTonnesPerDay:5,
 bunkerUsdPerTonne:600,portCosts:20000,otherCosts:0,commissionPct:2,contingencyPct:5};
 const out=calc(input);assert.ok(out);
 assert.equal(out.gross,853825);
 assert.equal(out.totalDays,33);
 assert.equal(out.fuelTonnes,165);
 assert.equal(out.bunkerCost,99000);
 assert.equal(out.operatingCost,396000);
 assert.equal(out.commission,17076.5);
 assert.equal(out.nonCommissionCost,540750);
 assert.equal(out.contribution,295998.5);
 assert.ok(Math.abs(out.breakEvenDayrate-22071.4285714)<0.001);
 assert.ok(Math.abs(out.contributionMarginPct-34.66)<0.02);
 const noPaid=calc({...input,billableDays:0});
 const tooMany=calc({...input,billableDays:31});
 const badPrice=calc({...input,bunkerUsdPerTonne:Infinity});
 assert.equal(noPaid,null);assert.equal(tooMany,null);assert.equal(badPrice,null);
});
test('Never inherit NavProfit private AIS, user logins, mock bunker data, made-up voyage distances or invoice API keys',()=>{
 assert.ok(html.includes('shipping-offshore-econ-v117t.js'));
 assert.ok(economics.includes('data/offshore-rate-evidence-v117s.json'));
 assert.ok(economics.includes('reported issuer dayrates')||economics.includes('historical issuer'));
 assert.ok(economics.includes('not a current charter offer')||economics.includes('not a current charter'));
 assert.ok(!economics.includes('BUNKER_PRICES')&&!economics.includes('MOCK_FUEL_PRICES'));
 assert.ok(!economics.includes('aisstream.io')&&!economics.includes('open.er-api.com'));
 assert.ok(!economics.includes('ANTHROPIC_API_KEY')&&!economics.includes('OilPriceAPI'));
 assert.ok(!economics.includes('2000; // fallback'));
 assert.ok(!economics.includes('localStorage'));
});
