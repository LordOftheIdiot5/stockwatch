import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);const {financialSummary,eventsFor,financialHTML,actionHTML}=require('../company-research.js');
const f={asOf:'2026-09-30',period:'Q3',currency:'DKK',sourceUrl:'https://example.com/report',metrics:{revenue:100,operatingIncome:20,adjustedOperatingIncome:30}};
test('period safe margins kept distinct',()=>{const r=financialSummary(f);assert.deepEqual(r.ratios.map(x=>x.value),[20,30]);assert.equal(r.period,'Q3');assert.equal(financialSummary({...f,sourceUrl:'javascript:bad'}),null);assert.deepEqual(financialSummary({...f,metrics:{revenue:0,operatingIncome:20}}).ratios,[])});
test('only explicit source-linked events for exact ticker',()=>{const a={ticker:'AAA',date:'2026-11-25',sourceUrl:'https://example.com/event'};assert.equal(eventsFor('AAA',[a,{...a,ticker:'BBB'},{...a,sourceUrl:'javascript:alert(1)'},{...a,date:'2026-02-30'}]).length,1);assert.match(actionHTML('AAA',[],null),/does not mean/)});
test('missing facts are not invented',()=>{assert.match(financialHTML(null),/No verified numeric statements/);assert.match(financialHTML(f),/20%/)});
