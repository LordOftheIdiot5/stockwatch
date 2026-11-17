import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);const S=require('../screener-v51.js');
const day='2026-11-16',a={ticker:'A',date:day,close:10,volume:20,changePct:2,rvol:1,currency:'NOK'},b={...a,ticker:'B',date:'2026-11-13',changePct:99},c={...a,ticker:'C',volume:0,changePct:100},d={...a,ticker:'D',referenceOnly:true,changePct:200},e={...a,ticker:'E',changePct:-4,currency:'SEK'};
test('ranking never ranks stale or nontrading observations',()=>{assert.deepEqual(S.rank([b,c,d,e,a],'gain',day).map(x=>x.ticker),['A','E','B','C','D']);assert.deepEqual(S.rank([a,b,e],'loss',day).map(x=>x.ticker),['E','A','B']);assert.equal(S.heatValue(b,'change',day),null);assert.equal(S.heatValue(c,'volume',day),null)});
test('currency and comparable filters compose',()=>{assert.deepEqual(S.filters([a,b,c,d,e],{session:day,currency:'NOK',coverage:'comparable'}),[a]);assert.equal(S.comparable({...a,date:'2026-02-30'},'2026-02-30'),false);assert.equal(S.metric({...a,thin:true},'volume',day),null);});

test('dated last price remains displayable outside ranking session',()=>{assert.equal(S.hasPrice(b),true);assert.equal(S.latestChange(b),99);assert.equal(S.metric(b,'gain',day),null);assert.equal(S.latestChange(c),null);assert.equal(S.hasPrice(d),false);assert.deepEqual(S.rank([d,b,a],'gain',day).map(x=>x.ticker),['A','B','D'])});

test('existing pair observations never become scanner signals',()=>{const r={referenceOnly:true,referenceId:'XCSE:MAERSK A',mic:'XCSE',symbol:'MAERSK A',unavailable:true};const pair={a:'MAERSK-A.CO',b:'MAERSK-B.CO',aPrice:19980,bPrice:20360,currency:'DKK',priceDate:day};const q=S.pairQuote(r,[pair]);assert.equal(q.close,19980);assert.equal(S.displayPrice({...r,pairQuote:q}).date,day);assert.equal(S.comparable({...r,pairQuote:q},day),false);assert.equal(S.pairQuote({...r,mic:'XSTO'},[pair]),null);assert.equal(S.pairQuote(r,[{...pair,currency:'SEK'}]),null)});

test('V61: expanded venue+FIGI exact share-class identity required',()=>{
 const mappings=[['BBG000BB48H2','HUSQB','HUSQ-B.ST'],['BBG000BG96K6','INVEA','INVE-A.ST'],['BBG000BCH127','VOLVA','VOLV-A.ST'],['BBG000BGD8Q1','SSABB','SSAB-B.ST'],['BBG000BB28Z4','HUSQA','HUSQ-A.ST']];
 for(const [figi,symbol,ticker] of mappings){
  const row={referenceOnly:true,registryOnly:true,expandedReference:true,mic:'XSTO',figi,symbol,ticker:'registry:XSTO:'+figi};
  const pair={a:ticker,b:'OTHER.ST',aPrice:12,bPrice:999,currency:'SEK',priceDate:day};
  const q=S.pairQuote(row,[pair]);assert.equal(q.close,12);assert.equal(q.ticker,ticker);
  assert.equal(S.comparable({...row,pairQuote:q},day),false);
  for(const bad of [{symbol:'WRONG'},{figi:'WRONG'},{mic:'XCSE'},{ticker:'registry:XSTO:WRONG'},{expandedReference:false}])assert.equal(S.pairQuote({...row,...bad},[pair]),null);
  assert.equal(S.pairQuote(row,[pair,pair]),null);
  assert.equal(S.pairQuote(row,[{...pair,aPrice:0}]),null);
 }
});

test('V72: remaining Norwegian and Swedish share-class observations have exact venue, currency and FIGI',()=>{
 const mappings=[['BBG000BKSXB7','ODFB','ODFB.OL','XOSL','NOK'],['BBG000BDD8Z8','WWIB','WWIB.OL','XOSL','NOK'],['BBG000BP71K9','KINVA','KINV-A.ST','XSTO','SEK'],['BBG000BP73C4','KINVB','KINV-B.ST','XSTO','SEK'],['BBG000BDZQP5','SSABA','SSAB-A.ST','XSTO','SEK'],['BBG000BCCG29','SCAB','SCA-B.ST','XSTO','SEK'],['BBG000BFQ1Y5','SCAA','SCA-A.ST','XSTO','SEK']];
 for(const [figi,symbol,ticker,mic,currency] of mappings){
  const row={referenceOnly:true,registryOnly:true,expandedReference:true,mic,figi,symbol,ticker:'registry:'+mic+':'+figi};
  const pair={a:ticker,b:'OTHER',aPrice:12,bPrice:99,currency,priceDate:day};
  assert.equal(S.pairQuote(row,[pair]).close,12);
  assert.equal(S.comparable({...row,pairQuote:S.pairQuote(row,[pair])},day),false);
  assert.equal(S.pairQuote(row,[{...pair,currency:'USD'}]),null);
  const wrong=mic==='XOSL'?'XSTO':'XOSL';
  assert.equal(S.pairQuote({...row,mic:wrong,ticker:'registry:'+wrong+':'+figi},[{...pair,currency:wrong==='XOSL'?'NOK':'SEK'}]),null);
 }
});
