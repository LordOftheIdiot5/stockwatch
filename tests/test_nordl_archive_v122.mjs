import test from 'node:test';
import assert from 'node:assert/strict';
import {planArchive} from '../scripts/nordl-archive-envelope-v122.mjs';
// Synthetic operator-policy fixture only. Never authorizes a real source.
const policy={policyId:'fixture-policy',sourceId:'fixture',seriesId:'fixture-series',entityId:'fixture-entity',metric:'fixture-metric',unit:'units',sourceUrl:'https://example.com/source',evidence:'test only',rights:{collect:'allowed',retain:'allowed',display:'blocked',export:'blocked'}};
const input={...policy,periodEnd:'2026-11-01',retrievedAt:'2026-11-02T00:00:00Z',value:10};
const asOf='2026-11-24T00:00:00Z';
test('retention must be explicitly approved independently of display',()=>{
 for(const retain of ['blocked','unreviewed'])assert.deepEqual(planArchive(input,{...policy,rights:{...policy.rights,retain}},asOf),{status:'blocked_retention',writes:[]});
});
test('repeated retrieval deduplicates revision but preserves receipt',()=>{
 const a=planArchive(input,policy,asOf),b=planArchive({...input,retrievedAt:'2026-11-03T00:00:00Z'},policy,asOf);
 assert.equal(a.objectKey,b.objectKey);assert.notEqual(a.receiptKey,b.receiptKey);assert.equal(a.publicEligible,false);
 assert.deepEqual(a,planArchive(input,policy,asOf));
});
test('correction retains original logical identity and creates revision',()=>{
 const a=planArchive(input,policy,asOf),b=planArchive({...input,value:11},policy,asOf);
 assert.equal(a.revision.logicalId,b.revision.logicalId);assert.notEqual(a.revision.revisionId,b.revision.revisionId);assert.notEqual(a.objectKey,b.objectKey);
});
test('future retrieval and policy mismatch cannot plan archive',()=>{
 assert.throws(()=>planArchive({...input,retrievedAt:'2027-01-01T00:00:00Z'},policy,asOf));
 assert.throws(()=>planArchive({...input,unit:'other'},policy,asOf));
});
