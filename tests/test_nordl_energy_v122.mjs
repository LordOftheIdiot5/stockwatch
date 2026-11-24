import test from 'node:test';
import assert from 'node:assert/strict';
import {energyPilot} from '../scripts/nordl-energy-pilot-v122.mjs';
const asOf='2026-11-24T00:28:10Z';
// Synthetic schema fixture, not a published observation.
const fixture={generated:asOf,reservoirs:{year:2026,week:46,zones:{NO2:{fill:.5,normal:.8,years:31},NO4:{fill:.9,normal:.8,years:31}}}};
test('percentage points, missing zones and separate reference identity',()=>{
 const p=energyPilot(fixture,asOf);assert.equal(p.results.length,2);assert.equal(p.missing.length,3);
 assert.equal(p.results[0].signal.differencePercentagePoints,-30);assert.equal(p.results[1].signal.differencePercentagePoints,10);
 assert.equal(p.results[0].actual.periodEnd,'2026-11-15');assert.notEqual(p.results[0].actual.logicalId,p.results[0].reference.logicalId);assert.equal(p.publicEligible,false);
});
test('invalid week, future vintage, low coverage, invalid units and stale data fail closed',()=>{
 for(const mutate of [d=>d.reservoirs.week=54,d=>d.generated='2026-12-01T00:00:00Z',d=>d.reservoirs.zones.NO2.years=1,d=>d.reservoirs.zones.NO2.fill=50]){
 const d=structuredClone(fixture);mutate(d);assert.ok(!energyPilot(d,asOf).results.some(x=>x.zone==='NO2'));
 }
 assert.equal(energyPilot(fixture,'2027-01-01T00:00:00Z').results.length,0);
});
