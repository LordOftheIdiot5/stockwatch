import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const source=fs.readFileSync(new URL('../v4.js',import.meta.url),'utf8');
const a=source.indexOf('function displayChartMapping('),b=source.indexOf('function displayChartCard(',a);
const {displayChartMapping,tvChartOptions}=Function(source.slice(a,b)+'\nreturn {displayChartMapping,tvChartOptions}')();
const read=p=>JSON.parse(fs.readFileSync(new URL('../'+p,import.meta.url),'utf8'));
const d=read('data/chart-display-symbols.json');
test('explicit mappings refer to actual universe IDs',()=>{
 const ids=new Set([...read('watchlist.json').tickers.map(r=>r.ticker),...read('data/research-targets.json').targets.map(r=>'ref:'+r.id),...read('data/research-expansion.json').records.map(r=>'registry:'+r.mic+':'+r.figi)]);
 assert.equal(d.records.length,17);
 assert.equal(new Set(d.records.map(r=>r.listingId)).size,17);
 for(const r of d.records){assert.ok(ids.has(r.listingId),r.listingId);assert.ok(displayChartMapping(r.listingId,d));}
 assert.equal(displayChartMapping('ref:XOSL:EQNR',d).mode,'external');
 assert.equal(displayChartMapping('unknown',d),null);
 assert.equal(displayChartMapping('a',{records:[{listingId:'a',symbol:'OSL:EQNR',mode:'embed'}]}),null);
 assert.equal(displayChartMapping('a',{records:[{listingId:'a',symbol:'javascript:evil',mode:'embed'}]}),null);
});
test('theme and chart style control preserve exact symbol',()=>{
 const dark=tvChartOptions('OMXSTO:VOLV_B','dark'),light=tvChartOptions('OMXSTO:VOLV_B','light','3');
 assert.equal(dark.backgroundColor,'#101b2c');assert.equal(light.backgroundColor,'#ffffff');
 assert.equal(light.symbol,dark.symbol);assert.equal(light.theme,'light');assert.equal(light.style,'3');
 assert.equal(light.allow_symbol_change,false);
});
