import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizeFintraffic, boundedJson, collectFintraffic, getPublicSnapshot } from '../worker/marine-ais-v120.mjs';

const NOW=1795460000000;
const MMSI=230949000;
const latest=NOW-60000;
const sample=(time=latest)=>({type:'Feature',mmsi:MMSI,
  geometry:{type:'Point',coordinates:[28.927335,61.856277]},
  properties:{mmsi:MMSI,sog:11.2,cog:189.5,heading:190,navStat:0,timestamp:30,timestampExternal:time}});
const meta={mmsi:MMSI,name:'HELGA',destination:'SAVONLINNA',shipType:70,imo:8325121,timestamp:NOW-120000};
const locations=(...features)=>({type:'FeatureCollection',features});
class Store {
 constructor(){this.objects=new Map()}
 async get(key){const x=this.objects.get(key);return x?{json:async()=>JSON.parse(x)}:null}
 async put(key,val){this.objects.set(key,val)}
}
function fakeFetch(url){
 const value=url.endsWith('/locations')?locations(sample()):[meta];
 return Promise.resolve(new Response(JSON.stringify(value),{headers:{'content-type':'application/json'}}));
}
function environment(){return {COLLECTOR_ENABLED:'true',PUBLIC_AIS_ENABLED:'true',AIS_BUCKET:new Store()}}
test('real vessel position with attributable and separately timed identity',()=>{
 const s=normalizeFintraffic(locations(sample()),[meta],NOW);
 assert.equal(s.positionCount,1);
 assert.equal(s.provider,'Fintraffic Digitraffic');
 assert.equal(s.license,'CC BY 4.0');
 assert.equal(s.positions[0].name,'HELGA');
 assert.equal(s.positions[0].destinationAisReported,'SAVONLINNA');
 assert.equal(s.positions[0].positionReportedAt,new Date(latest).toISOString());
 assert.notEqual(s.positions[0].metadataReportedAt,s.positions[0].positionReportedAt);
 assert.equal(s.positions[0].operator,undefined);
 assert.equal(s.positions[0].eta,undefined);
});
test('reject malformed, stale, future and non-commercial positions',()=>{
 assert.throws(()=>normalizeFintraffic({},[],NOW),/invalid_locations/);
 assert.throws(()=>normalizeFintraffic(locations(sample()),{},NOW),/invalid_metadata/);
 assert.throws(()=>normalizeFintraffic(locations(sample(NOW-31*60000)),[meta],NOW),/no_fresh/);
 assert.throws(()=>normalizeFintraffic(locations(sample(NOW+3*60000)),[meta],NOW),/no_fresh/);
 assert.throws(()=>normalizeFintraffic(locations(sample()),[{...meta,shipType:30}],NOW),/no_fresh/);
 assert.throws(()=>normalizeFintraffic(locations(sample()),[],NOW),/no_fresh/);
 const bad=sample();bad.geometry.coordinates=[190,20];
 assert.throws(()=>normalizeFintraffic(locations(bad),[meta],NOW),/no_fresh/);
});
test('deduplicated MMSI; invalid AIS sentinel measurements become null',()=>{
 const older=sample(NOW-150000);
 const newer=sample(NOW-10000);
 newer.properties.sog=102.3;newer.properties.cog=360;newer.properties.heading=511;
 const s=normalizeFintraffic(locations(older,newer),[meta],NOW);
 assert.equal(s.positionCount,1);
 assert.equal(s.positions[0].positionReportedAt,new Date(NOW-10000).toISOString());
 assert.equal(s.positions[0].speedKnots,null);
 assert.equal(s.positions[0].courseDegrees,null);
 assert.equal(s.positions[0].headingDegrees,null);
});
test('upstream allowlist and bounded body limits',async()=>{
 await assert.rejects(()=>boundedJson('https://other.example/something',fakeFetch),/not_allowlisted/);
 await assert.rejects(()=>boundedJson('https://meri.digitraffic.fi/api/ais/v1/locations',fakeFetch,20),/too_large/);
 const data=await boundedJson('https://meri.digitraffic.fi/api/ais/v1/locations',fakeFetch);
 assert.equal(data.features.length,1);
});
test('scheduled collector writes R2 once, reader serves only stored data',async()=>{
 const e=environment();
 const result=await collectFintraffic(e,{nowMs:NOW,fetcher:fakeFetch});
 assert.equal(result.status,'ok');
 assert.equal(result.positionCount,1);
 assert.equal(e.AIS_BUCKET.objects.size,2);
 const response=await getPublicSnapshot(e,NOW+30000);
 assert.equal(response.status,200);
 const data=await response.json();
 assert.equal(data.positions.length,1);
 assert.equal(data.snapshotAgeSeconds,30);
 assert.equal(response.headers.get('access-control-allow-origin'),'https://stocks.nordl.dev');
 const dedup=await collectFintraffic(e,{nowMs:NOW+60000,fetcher:()=>{throw Error('must not fetch')}});
 assert.equal(dedup.status,'too_recent');
});
test('upstream error cannot overwrite last good snapshot',async()=>{
 const e=environment();
 await collectFintraffic(e,{nowMs:NOW,fetcher:fakeFetch});
 const key='ais/v120/fintraffic/latest.json';
 const previous=e.AIS_BUCKET.objects.get(key);
 const outcome=await collectFintraffic(e,{nowMs:NOW+200000,
  fetcher:async()=>new Response('failure',{status:503})});
 assert.equal(outcome.status,'source_error');
 assert.equal(e.AIS_BUCKET.objects.get(key),previous);
});
test('disabled and stale sources never display phantom ships',async()=>{
 const e=environment();
 e.PUBLIC_AIS_ENABLED='false';
 let result=await getPublicSnapshot(e,NOW);
 assert.equal(result.status,503);
 assert.deepEqual((await result.json()).positions,[]);
 e.PUBLIC_AIS_ENABLED='true';
 await collectFintraffic(e,{nowMs:NOW,fetcher:fakeFetch});
 result=await getPublicSnapshot(e,NOW+11*60000);
 assert.equal(result.status,503);
 assert.deepEqual((await result.json()).positions,[]);
 result=await getPublicSnapshot(e,NOW+9*60000);
 assert.equal(result.status,200);
 assert.equal((await result.json()).positions.length,1);
});
test('disabled collector cannot collect; absent storage never claims healthy',async()=>{
 assert.deepEqual(await collectFintraffic({COLLECTOR_ENABLED:'false'}),{status:'disabled'});
 assert.equal((await getPublicSnapshot({PUBLIC_AIS_ENABLED:'true'},NOW)).status,503);
});