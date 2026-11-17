import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../v4.js',import.meta.url),'utf8');
const css=readFileSync(new URL('../v4.css',import.meta.url),'utf8');
const start=src.indexOf("function marketHeatData("),end=src.indexOf("function overview()",start);
assert.ok(start>=0&&end>start);
const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const P=x=>(x>0?'+':'')+x.toFixed(2)+'%';
const {marketHeatData,workspaceHeatmap}=Function('E','P',src.slice(start,end)+'\nreturn {marketHeatData,workspaceHeatmap};')(E,P);
const rows=[
 {ticker:'A.OL',name:'A',sector:'Industry',close:100,changePct:2.7},
 {ticker:'B.ST',name:'B',sector:'Shipping',close:50,changePct:-6.1},
 {ticker:'C.CO',name:'C',sector:'Industry',close:25,changePct:0},
 {ticker:'NO.OL',name:'No price',sector:'Industry',close:null,changePct:3},
 {ticker:'BAD.OL',name:'No change',sector:'Industry',close:10,changePct:null},
 {ticker:'OLD.OL',name:'Unavailable',sector:'Industry',close:9,changePct:5,unavailable:true}
];
test('heatmap excludes missing prices and missing changes, retains zero',()=>{
 assert.deepEqual(marketHeatData(rows).map(r=>r.ticker),['A.OL','B.ST','C.CO']);
 assert.deepEqual(marketHeatData(rows,'Industry').map(r=>r.ticker),['A.OL','C.CO']);
 assert.deepEqual(marketHeatData(rows,'Missing'),[]);
});
test('heatmap uses observed values, bounded color intensity, and functional links',()=>{
 const html=workspaceHeatmap(rows);
 assert.equal((html.match(/class="sw-heat-cell /g)||[]).length,3);
 assert.match(html,/positive" data-strength="3"/);
 assert.match(html,/negative" data-strength="5"/);
 assert.match(html,/flat" data-strength="0"/);
 assert.match(html,/company.html\?ticker=B\.ST/);
 assert.match(html,/-6.10%/);
 assert.doesNotMatch(html,/NO.OL|BAD.OL|OLD.OL/);
 assert.match(workspaceHeatmap(rows,'Missing'),/No observed price changes/);
});
test('workspace has theme-aware visuals, pagination and candidate provenance',()=>{
 assert.match(css,/body\[data-theme="light"\]\{--sw-heat-pos:/);
 assert.match(css,/prefers-reduced-motion/);
 assert.match(src,/const pageSize=50/);
 assert.match(src,/a\.slice\(\(currentPage-1\)\*pageSize,currentPage\*pageSize\)/);
 assert.match(src,/Candidate — not verified/);
 assert.match(src,/Multiple candidates — unresolved/);
 assert.match(src,/https:\/\/leivro\.com\//);
});
