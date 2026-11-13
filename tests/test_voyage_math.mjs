import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const source=fs.readFileSync(new URL('../v4.js', import.meta.url),'utf-8');
const start=source.indexOf('function voyageCostScenario(v){');
const end=source.indexOf('\nfunction renderVoyageEstimator(){',start);
assert.ok(start>0 && end>start,'Standalone voyage model exists');
const model=vm.runInNewContext('('+source.slice(start,end).trim()+')');

test('voyage scenario model computes fuel, hire, ballast, and per-tonne cost',()=>{
 const v={distance:2400,ballast:0,speed:10,burn:20,portDays:2,portBurn:5,
          fuel:500,cargo:40000,hire:12000,portFees:30000,other:0,contingency:0};
 const r=model(v);
 // 10 days steaming + 2 days in port; 210 t fuel, $105k fuel, $144k hire, $30k fees.
 assert.equal(r.seaDays,10);
 assert.equal(r.fuelTonnes,210);
 assert.equal(r.fuelUSD,105000);
 assert.equal(r.hireUSD,144000);
 assert.equal(r.total,279000);
 assert.equal(r.perTonne,6.975);
});

test('ballast and contingency alter the modeled voyage, never a benchmark',()=>{
 const v={distance:2400,ballast:2400,speed:10,burn:20,portDays:2,portBurn:5,
          fuel:500,cargo:40000,hire:12000,portFees:30000,other:0,contingency:10};
 const r=model(v);
 assert.equal(r.seaDays,20);
 assert.ok(r.total>279000);
 assert.ok(Math.abs(r.total-r.subtotal*1.1)<1e-8);
 assert.match(source,/NOT Baltic assessment/);
 assert.match(source,/Route selection is a label only/);
});

test('IMF feed explicitly permission-gated and UNCTAD LSCI is no-price',()=>{
 assert.match(source,/No automated IMF feed is downloaded/);
 assert.match(source,/x.isActualRate===false&&x.frequency==='monthly'/);
 assert.match(source,/CC BY 3.0 IGO/);
});
