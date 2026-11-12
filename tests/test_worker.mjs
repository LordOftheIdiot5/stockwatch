import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
const content=readFileSync(new URL('../worker/index.js',import.meta.url),'utf8');
const {default:worker}=await import('data:text/javascript;charset=utf-8,'+encodeURIComponent(content));
const url='https://research.example.workers.dev';
function req(path,init={}){return new Request(url+path,init)}
test('unbound D1 fails closed',async()=>{
  const response=await worker.fetch(req('/api/health'),{});
  assert.equal(response.status,503);
  assert.deepEqual(await response.json(),{status:'unconfigured',storage:'d1'});
  assert.equal((await worker.fetch(req('/api/news'),{})).status,503);
});
test('health reads actual database row count',async()=>{
  const db={prepare(sql){assert.match(sql,/COUNT\(\*\)/);return {first:async()=>({articles:22})}}};
  const result=await worker.fetch(req('/api/health'),{DB:db});
  assert.equal(result.status,200);assert.equal((await result.json()).articles,22);
});
test('ingestion rejects bad auth/body and oversize',async()=>{
  const db={prepare:()=>{throw Error('must not touch DB')},batch:()=>{throw Error('must not batch')}};
  const un=await worker.fetch(req('/api/news/ingest',{method:'POST',body:'{}'}),{DB:db,NEWS_INGEST_TOKEN:'secret'});
  assert.equal(un.status,403);
  const bad=await worker.fetch(req('/api/news/ingest',{method:'POST',headers:{authorization:'Bearer secret'},body:'null'}),{DB:db,NEWS_INGEST_TOKEN:'secret'});
  assert.equal(bad.status,400);
  const big=await worker.fetch(req('/api/news/ingest',{method:'POST',headers:{authorization:'Bearer secret'},body:'x'.repeat(450001)}),{DB:db,NEWS_INGEST_TOKEN:'secret'});
  assert.equal(big.status,413);
});
test('valid article upsert is idempotent',async()=>{
  let query='',bound=null,batches=0;
  const db={prepare(sql){query=sql;return {bind(...xs){bound=xs;return {}}}},async batch(x){batches++;assert.equal(x.length,1)}};
  const data={items:[{id:'ABC:hash',ticker:'ABC.OL',name:'ABC',sector:'Energy',headline:'ABC reports earnings',type:'news',url:'https://issuer.example.org/news',published:'2026-11-12T10:00:00Z',match:'name_mentioned'}]};
  const result=await worker.fetch(req('/api/news/ingest',{method:'POST',headers:{authorization:'Bearer secret','content-type':'application/json'},body:JSON.stringify(data)}),{DB:db,NEWS_INGEST_TOKEN:'secret'});
  assert.equal(result.status,200);assert.equal((await result.json()).accepted,1);
  assert.match(query,/ON CONFLICT\(id\)/);assert.equal(bound[1],'ABC.OL');assert.equal(batches,1);
});
