import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../v4.js',import.meta.url),'utf8');
const start=source.indexOf('function switchEstimate('),end=source.indexOf('function spreadCurrency(',start);
if(start<0||end<start)throw new Error('Could not find switch estimator');
const estimate=Function(source.slice(start,end)+';return switchEstimate;')();
const pair={aPrice:100,bPrice:80,meanRatio:1.15};
test('switching A to B with no costs preserves gross buying power',()=>{
 const x=estimate(pair,'A-to-B',80,0,0,0);
 assert.equal(x.shares,100);assert.equal(x.remainder,0);assert.equal(x.drag,0);
 assert.equal(x.baseline,92);
});
test('switching with fees and slippage never overspends',()=>{
 const x=estimate(pair,'A-to-B',100,0.15,0.2,15);
 assert.ok(x.shares>0&&x.shares<125);
 const proceeds=100*100*(1-.002)-Math.max(15,100*100*(1-.002)*.0015);
 const cost=x.shares*80*(1+.002)+Math.max(15,x.shares*80*(1+.002)*.0015);
 assert.ok(proceeds>=cost-1e-7);assert.ok(x.drag>0);
});
test('reverse direction uses reciprocal of historical mean',()=>{
 const x=estimate(pair,'B-to-A',115,0,0,0);
 assert.equal(x.shares,92);assert.ok(Math.abs(x.baseline-100)<1e-9);
});
test('invalid, missing, negative inputs are rejected',()=>{
 for(const shares of [0,-1,Number.POSITIVE_INFINITY,NaN])assert.equal(estimate(pair,'A-to-B',shares,0,0,0),null);
 assert.equal(estimate({...pair,aPrice:0},'A-to-B',10,0,0,0),null);
 assert.equal(estimate(pair,'A-to-B',10,-1,0,0),null);
});
