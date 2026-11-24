import test from 'node:test';
import assert from 'node:assert/strict';
import {createPolicyRegistry} from '../scripts/nordl-source-policy-v122.mjs';
import {planArchive} from '../scripts/nordl-archive-envelope-v122.mjs';
const policy={policyId:'fixture',sourceId:'fixture',seriesId:'series',entityId:'entity',metric:'metric',unit:'units',sourceUrl:'https://example.com/source',evidence:'synthetic test only',rights:{collect:'allowed',retain:'unreviewed',display:'blocked',export:'blocked'}};
const input={...policy,value:3,periodEnd:'2026-11-01',retrievedAt:'2026-11-02T00:00:00Z'};
const asOf='2026-11-24T00:00:00Z';
test('payload cannot grant itself retention or display',()=>{
 const registry=createPolicyRegistry([policy]), incoming={...input,rights:{collect:'allowed',retain:'allowed',display:'allowed',export:'allowed'}};
 const trusted=registry.resolve('fixture',incoming,asOf);
 assert.equal(trusted.rights.retain,'unreviewed');
 assert.equal(planArchive(incoming,trusted,asOf).status,'blocked_retention');
});
test('registry snapshots policy and rejects unknown or mismatched identity',()=>{
 const p=structuredClone(policy),registry=createPolicyRegistry([p]);p.rights.retain='allowed';
 assert.equal(registry.resolve('fixture',input,asOf).rights.retain,'unreviewed');
 assert.throws(()=>registry.resolve('unknown',input,asOf));
 assert.throws(()=>registry.resolve('fixture',{...input,unit:'other'},asOf));
 assert.throws(()=>createPolicyRegistry([policy,policy]));
});
