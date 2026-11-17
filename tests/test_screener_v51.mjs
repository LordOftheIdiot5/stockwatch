import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);const S=require('../screener-v51.js');
const day='2026-11-16',a={ticker:'A',date:day,close:10,volume:20,changePct:2,rvol:1,currency:'NOK'},b={...a,ticker:'B',date:'2026-11-13',changePct:99},c={...a,ticker:'C',volume:0,changePct:100},d={...a,ticker:'D',referenceOnly:true,changePct:200},e={...a,ticker:'E',changePct:-4,currency:'SEK'};
test('ranking never ranks stale or nontrading observations',()=>{assert.deepEqual(S.rank([b,c,d,e,a],'gain',day).map(x=>x.ticker),['A','E','B','C','D']);assert.deepEqual(S.rank([a,b,e],'loss',day).map(x=>x.ticker),['E','A','B']);assert.equal(S.heatValue(b,'change',day),null);assert.equal(S.heatValue(c,'volume',day),null)});
test('currency and comparable filters compose',()=>{assert.deepEqual(S.filters([a,b,c,d,e],{session:day,currency:'NOK',coverage:'comparable'}),[a]);assert.equal(S.comparable({...a,date:'2026-02-30'},'2026-02-30'),false);assert.equal(S.metric({...a,thin:true},'volume',day),null);});

test('dated last price remains displayable outside ranking session',()=>{assert.equal(S.hasPrice(b),true);assert.equal(S.latestChange(b),99);assert.equal(S.metric(b,'gain',day),null);assert.equal(S.latestChange(c),null);assert.equal(S.hasPrice(d),false);assert.deepEqual(S.rank([d,b,a],'gain',day).map(x=>x.ticker),['A','B','D'])});

test('existing pair observations never become scanner signals',()=>{const r={referenceOnly:true,referenceId:'XCSE:MAERSK A',mic:'XCSE',symbol:'MAERSK A',unavailable:true};const pair={a:'MAERSK-A.CO',b:'MAERSK-B.CO',aPrice:19980,bPrice:20360,currency:'DKK',priceDate:day};const q=S.pairQuote(r,[pair]);assert.equal(q.close,19980);assert.equal(S.displayPrice({...r,pairQuote:q}).date,day);assert.equal(S.comparable({...r,pairQuote:q},day),false);assert.equal(S.pairQuote({...r,mic:'XSTO'},[pair]),null);assert.equal(S.pairQuote(r,[{...pair,currency:'SEK'}]),null)});
