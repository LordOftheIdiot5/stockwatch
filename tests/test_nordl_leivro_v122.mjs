import test from 'node:test';
import assert from 'node:assert/strict';
import {leivroPilot} from '../scripts/nordl-leivro-pilot-v122.mjs';
const asOf='2026-11-24T01:00:00Z',source='https://data.energystar.gov/d/wati-2tfp';
// Synthetic collector-shaped fixture; never published as actual source data.
const fixture={schema_version:1,status:'ok',source,dataset_id:'wati-2tfp',full_snapshot:true,checked_at_utc:'2026-11-24T00:00:00.123456+00:00',source_rows:6,normalized_rows:5,rejected_rows:1,products:Array.from({length:5},(_,i)=>({energy_star_unique_id:String(i+1),brand:'fixture',model_number:'test-'+i,source}))};
test('catalog count preserves retrieval basis and blocks public use',()=>{
 const p=leivroPilot(fixture,asOf);assert.equal(p.results.length,1);assert.equal(p.results[0].observation.value,5);assert.equal(p.results[0].observation.publishedAt,null);assert.equal(p.publicEligible,false);
});
test('partial, duplicate, unknown source, count mismatch, future date rejected',()=>{
 for(const mutate of [d=>d.full_snapshot=false,d=>d.products[1].energy_star_unique_id='1',d=>d.source='https://example.com',d=>d.source_rows=20,d=>d.checked_at_utc='2026-12-01T00:00:00Z']){
 const d=structuredClone(fixture);mutate(d);assert.equal(leivroPilot(d,asOf).results.length,0);
 }
});
