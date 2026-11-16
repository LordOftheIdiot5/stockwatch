import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {points,compareSeries,newsRelevant}=require('../terminal.js');
test('reject invalid dates and conflicting values',()=>{
 assert.deepEqual(points([{date:'2025-02-30',value:2},{date:'2025-01-01',value:1},{date:'2025-01-01',value:3},{date:'2025-01-02',value:4}]),[{date:'2025-01-02',value:4}]);
});
test('normalization uses shared dates and no forward fill',()=>{
 const a={history:[{date:'2025-01-01',value:10},{date:'2025-01-02',value:20},{date:'2025-01-03',value:30}]};
 const b={history:[{date:'2025-01-02',value:5},{date:'2025-01-03',value:10},{date:'2025-01-04',value:15}]};
 const r=compareSeries([a,b],0);
 assert.deepEqual(r[0].points.map(x=>x.value),[100,150]);
 assert.deepEqual(r[1].points.map(x=>x.value),[100,200]);
 assert.deepEqual(compareSeries([a,{history:[{date:'2025-02-01',value:1}]}],0),[]);
});
test('news suppresses unrelated sports and venue headlines',()=>{
 assert.equal(newsRelevant({headline:'Traffic accident at SAP Arena',material:3}),false);
 assert.equal(newsRelevant({headline:'Formula 1 team order review',material:3}),false);
 assert.equal(newsRelevant({headline:'Ferrari earnings guidance',material:2}),true);
 assert.equal(newsRelevant({kind:'disclosure',headline:'Correction'}),true);
});