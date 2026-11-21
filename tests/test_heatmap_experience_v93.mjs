import {createRequire} from 'node:module';
import {test} from 'node:test';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {countStates,describe}=require('../heatmap-experience-v93.js');
test('counts only existing visible tiles',()=>{
 assert.deepEqual(countStates(['sw-heat-cell positive','sw-heat-cell negative','sw-heat-cell flat',
  'sw-heat-cell no-data','other']),{up:1,down:1,flat:1,unavailable:1,total:4});
});
test('missing data never becomes a positive return',()=>{
 const r=countStates(['sw-heat-cell positive no-data','sw-heat-cell negative no-data']);
 assert.equal(r.unavailable,2);assert.equal(r.up+r.down,0);
});
test('empty tiles do not fabricate breadth',()=>{
 assert.deepEqual(countStates([]),{up:0,down:0,flat:0,unavailable:0,total:0});
});
test('unrecognized class entries do not count',()=>{
 assert.equal(countStates([null,4,{},'positive']).total,0);
});
test('dated observed tile keeps date and ticker',()=>{
 const d=describe({title:'Example · +2.42% · 2026-11-20 · NOK',
  ticker:'ABC.OL',change:'+2.42%',classes:'sw-heat-cell positive'});
 assert.equal(d.date,'2026-11-20');assert.equal(d.ticker,'ABC.OL');
 assert.equal(d.status,'Gain');assert.match(d.note,/2026-11-20/);
});
test('retained data visibly remains historical only',()=>{
 const d=describe({title:'Example · -3.1% · 2026-11-19 · saved movement',
  ticker:'ABC.OL',classes:'sw-heat-cell negative'});
 assert.equal(d.retained,true);assert.match(d.note,/not a live price/i);
});
test('unavailable stays unavailable even with dated title',()=>{
 const d=describe({title:'Example · Older price · 2026-11-18',
  classes:'sw-heat-cell no-data'});
 assert.equal(d.status,'No verified movement');assert.equal(d.css,'sw93-unavailable');
});
test('unknown date remains explicitly unknown',()=>{
 const d=describe({title:'Example · unavailable',classes:'sw-heat-cell no-data'});
 assert.equal(d.date,'');assert.match(d.note,/No confirmed observation date/);
});
test('fallback label is used when title missing',()=>{
 const d=describe({label:'Company A · no data',classes:'sw-heat-cell no-data'});
 assert.equal(d.details,'Company A · no data');
});
test('untrusted title is capped as plain text',()=>{
 const d=describe({title:'<img onerror=alert(1)>'+('a'.repeat(900)),
  classes:'sw-heat-cell positive'});
 assert.ok(d.details.length<=550);assert.match(d.details,/<img/);
});
test('never invent a missing change percentage',()=>{
 const d=describe({title:'Unknown',change:null,classes:'sw-heat-cell flat'});
 assert.equal(d.change,'');assert.equal(d.status,'Flat movement');
});

test('saved movement is retained even if it is not described as older price',()=>{
 const d=describe({title:'Example · -3% · 2026-11-19 · saved movement',
   classes:'sw-heat-cell negative'});
 assert.equal(d.retained,true);
 assert.match(d.note,/not a live price/i);
});
test('no-data tile does not display its descriptive text as a percentage',()=>{
 const d=describe({title:'Reference · No volume',change:'No volume',classes:'sw-heat-cell no-data'});
 assert.equal(d.change,'');
 assert.equal(d.status,'No verified movement');
});
