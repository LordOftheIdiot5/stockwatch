import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const code=fs.readFileSync(new URL('../v4.js',import.meta.url),'utf8');
const a=code.indexOf('function chartSeries('),b=code.indexOf('function lineGraph(',a);
const {chartSeries,chartWindow,chartCoordinates}=Function(code.slice(a,b)+'\nreturn {chartSeries,chartWindow,chartCoordinates}')();
test('real calendar spacing, not equally spaced observations',()=>{
 const s=chartSeries([{date:'2026-01-11',value:10},{date:'2026-01-01',value:4},{date:'2026-01-02',value:7}]);
 const p=chartCoordinates(s).points;
 assert.equal(s[0].date,'2026-01-01');
 assert.ok(Math.abs((p[1].x-p[0].x)/(p[2].x-p[0].x)-.1)<1e-9);
});
test('missing, invalid and conflicting observations excluded, zero retained',()=>{
 const s=chartSeries([{date:'2026-01-01',value:null},{date:'2026-01-02',value:0},{date:'2026-01-03',value:1},{date:'2026-01-03',value:2},{date:'2026-02-30',value:8},{date:'bad',value:1},{date:'2026-01-04',value:''}]);
 assert.deepEqual(s.map(x=>x.value),[0]);
});
test('window anchored to latest actual observation; constant values are finite',()=>{
 const s=[{date:'2025-01-01',value:8},{date:'2025-02-01',value:8}];
 assert.equal(chartWindow(s,10).length,1);
 assert.equal(chartWindow(s,0).length,2);
 assert.ok(chartCoordinates(chartSeries(s)).points.every(p=>Number.isFinite(p.y)));
});
