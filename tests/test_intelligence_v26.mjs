import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const src=fs.readFileSync(new URL('../v4.js',import.meta.url),'utf8');
const a=src.indexOf('function intelligenceGraph('),b=src.indexOf('function activeIntelligenceGraph(',a);
const {intelligenceGraph,graphNeighborhood}=Function(src.slice(a,b)+'\nreturn {intelligenceGraph,graphNeighborhood}')();
const rules=JSON.parse(fs.readFileSync(new URL('../data/intelligence-context.json',import.meta.url),'utf8'));
const rows=[{ticker:'FRO.OL',name:'Frontline',sector:'Shipping & offshore',exchange:'Oslo'},{ticker:'ref:XOSL:BWLPG',referenceId:'XOSL:BWLPG',referenceOnly:true,name:'BW LPG',sector:'Shipping & offshore',exchange:'Oslo',mappingStatus:'candidate',figi:'BBG000BLNNH6'},{ticker:'TEST.OL',name:'Test',sector:'Other',exchange:'Oslo'}];
test('typed graph separates research context from identity evidence',()=>{
 const g=intelligenceGraph(rows,rules,{figiCandidates:[{ticker:'FRO.OL',figi:'BBG000BLNNH7'}]});
 const ids=new Set(g.nodes.map(n=>n.id));assert.equal(ids.size,g.nodes.length);
 assert.ok(g.edges.every(e=>ids.has(e.from)&&ids.has(e.to)&&e.evidence));
 assert.deepEqual(new Set(g.edges.map(e=>e.type)),new Set(['classified_as','directory_venue','candidate_identifier','research_context']));
 assert.ok(g.edges.filter(e=>e.type==='research_context').every(e=>e.from.startsWith('sector:')&&e.to.startsWith('dataset:')));
 const n=graphNeighborhood(g,'FRO.OL');assert.equal(n.peers.length,1);assert.equal(n.context.length,4);
 assert.equal(n.peers[0].referenceOnly,true);
 assert.ok(n.direct.some(x=>x.relation==='candidate_identifier'&&x.evidence.includes('not independently verified')));
 assert.equal(graphNeighborhood(g,'TEST.OL').context.length,0);
 assert.equal(graphNeighborhood(g,'missing'),null);
});
test('multiple or stale candidates not promoted to identity edges',()=>{
 const g=intelligenceGraph([{...rows[1],mappingStatus:'ambiguous'},rows[0]],rules,{figiCandidates:[{ticker:'FRO.OL',figi:'BBG000BLNNH7'},{ticker:'FRO.OL',figi:'BBG000BLNNH8'}]});
 assert.equal(g.edges.filter(e=>e.type==='candidate_identifier').length,0);
});
test('configured datasets point to real repository series',()=>{
 for(const d of rules.datasets){
  const data=JSON.parse(fs.readFileSync(new URL('../'+d.file,import.meta.url),'utf8'));
  assert.ok(Array.isArray(data.series),d.id);
  if(d.key)assert.ok(data.series.some(s=>s.key===d.key),d.id);
 }
});
