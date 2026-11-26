const {test}=require('node:test'),assert=require('node:assert/strict'),{build}=require('../scripts/price_source_queue.cjs');
const sample=()=>({generated:'2026-11-19T20:00:00Z',summary:{listings:4,missingPrice:3},records:[{id:'a',venue:'Stockholm',priceStatus:'missing'},{id:'b',venue:'Oslo',priceStatus:'missing',mic:'XOSL',isin:'NO0000000001'},{id:'c',venue:'London',priceStatus:'missing'},{id:'d',venue:'Helsinki',priceStatus:'scanner'}]});
test('assign missing listings once with no implied entitlements',()=>{const v=build(sample());assert.equal(v.queues.nasdaq_nordic.missing,1);assert.equal(v.queues.euronext.missing,1);assert.equal(v.queues.other.missing,1);for(const q of Object.values(v.queues))for(const r of q.records){assert.equal(r.collectionEnabled,false);assert.equal(r.publicDisplayApproved,false);assert.equal(r.historicalRetentionApproved,false);assert.equal(r.commercialExportApproved,false)}});
test('refuse duplicate IDs and denominator mismatch',()=>{let s=sample();s.records[3].id='a';assert.throws(()=>build(s),/duplicate/);s=sample();s.summary.missingPrice=2;assert.throws(()=>build(s),/denominator/)});

test('Nasdaq private-use confirmation does not enable collection or publication',()=>{
 const q=build(sample()).queues.nasdaq_nordic;
 assert.equal(q.privateAnalysisConfirmed,true);
 assert.equal(q.reportAccessVerified,false);
 assert.equal(q.rightsEvidenceDate,'2026-11-25');
 assert.equal(q.records[0].collectionEnabled,false);
 assert.equal(q.records[0].publicDisplayApproved,false);
});
test('separate checksum-valid ISIN/MIC pairs from candidate FIGI/MIC and incomplete identity',()=>{
 const s=sample();
 s.records[0].mic='XSTO';s.records[0].figi='BBG000BXRMY9';
 s.records[1].isin='NO0010096985';
 s.records[2].isin='GB0000000000';s.records[2].mic='XLON';
 const q=build(s).queues;
 assert.deepEqual(q.nasdaq_nordic.readiness,{isinMic:0,figiMicWithoutISIN:1,otherIdentity:0});
 assert.equal(q.nasdaq_nordic.records[0].next,'resolve_exact_isin_for_figi_and_mic');
 assert.equal(q.euronext.readiness.isinMic,1);
 assert.equal(q.other.readiness.otherIdentity,1);
 const {validISIN}=require('../scripts/price_source_queue.cjs');
 assert.equal(validISIN('NO0010096985'),true);
 assert.equal(validISIN('NO0010096986'),false);
});
