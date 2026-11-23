/* Stockwatch V120b: source-verified Fintraffic AIS collector.
 * Source Fintraffic Digitraffic https://www.digitraffic.fi/en/marine-traffic/
 * Reuse CC BY 4.0 https://www.digitraffic.fi/en/terms-of-service/
 * R2 storage only. Scheduled collection only. Public read endpoint is OFF by
 * default and never fetches the upstream service on a visitor request.
 */
const API = 'https://meri.digitraffic.fi/api/ais/v1/';
const TERMS = 'https://www.digitraffic.fi/en/terms-of-service/';
const LICENSE = 'https://creativecommons.org/licenses/by/4.0/';
const SNAP = 'ais/v120/fintraffic/latest.json';
const HEALTH = 'ais/v120/fintraffic/health.json';
const MAX_POSITION_AGE = 30 * 60 * 1000;
const MAX_SNAPSHOT_AGE = 10 * 60 * 1000;
const MIN_FETCH_INTERVAL = 3 * 60 * 1000;
const MAX_FETCH_BYTES = 12 * 1024 * 1024;
const MAX_PUBLIC_ROWS = 2500;
const MAX_FUTURE_MS = 2 * 60 * 1000;
const MAX_META_AGE = 365 * 24 * 3600 * 1000;
const ALLOWED_CLASSES = new Set([52, 60, 70, 80, 90]); // commercial types only
const FRONTEND = 'https://stocks.nordl.dev';
const num = x => typeof x === 'number' && Number.isFinite(x) ? x : null;
const mmsi = x => Number.isInteger(x) && x >= 100000000 && x <= 999999999 ? x : null;
const utc = ms => new Date(ms).toISOString();
const stringField = (x, max) => typeof x === 'string'
  ? x.replace(/[\u0000-\u001f\u007f]/g, '').trim().slice(0, max) || null : null;
const className = code => ({52:'Tug',60:'Passenger',70:'Cargo',80:'Tanker',90:'Other AIS type (unverified)'})[code] || null;

export function normalizeFintraffic(locations, metadata, nowMs = Date.now()) {
  if (!locations || locations.type !== 'FeatureCollection' ||
      !Array.isArray(locations.features) || locations.features.length > 20000 ||
      locations.features.length === 0) throw Error('invalid_locations');
  if (!Array.isArray(metadata) || metadata.length > 100000) throw Error('invalid_metadata');
  const lookups = new Map();
  for (const meta of metadata) {
    if (!meta || typeof meta !== 'object') continue;
    const id = mmsi(meta.mmsi), kind = num(meta.shipType);
    const updated = num(meta.timestamp);
    if (!id || !ALLOWED_CLASSES.has(kind) || (kind === 90 && !(Number.isInteger(meta.imo) && meta.imo >= 1000000 && meta.imo <= 9999999)) || updated === null ||
        updated < nowMs - MAX_META_AGE || updated > nowMs + MAX_FUTURE_MS) continue;
    const old = lookups.get(id);
    if (!old || updated > old.timestamp) lookups.set(id, meta);
  }
  const vessels = new Map();
  for (const f of locations.features) {
    if (!f || f.type !== 'Feature' || f.geometry?.type !== 'Point') continue;
    const p = f.properties;
    const coords = f.geometry.coordinates;
    if (!p || !Array.isArray(coords) || coords.length < 2) continue;
    const id = mmsi(p.mmsi), sourceId = f.mmsi == null ? id : mmsi(f.mmsi);
    const longitude = num(coords[0]), latitude = num(coords[1]);
    const time = num(p.timestampExternal), meta = lookups.get(id);
    if (!id || id !== sourceId || !meta || longitude === null || latitude === null ||
        longitude < -180 || longitude > 180 || latitude < -90 || latitude > 90 ||
        time === null || time < nowMs - MAX_POSITION_AGE || time > nowMs + MAX_FUTURE_MS ||
        time < 1577836800000) continue;
    const sog = num(p.sog), cog = num(p.cog), heading = num(p.heading);
    const observation = {
      mmsi: id, imo: Number.isInteger(meta.imo) && meta.imo >= 1000000 && meta.imo <= 9999999 ? meta.imo : null,
      name: stringField(meta.name, 100),
      vesselClass: className(meta.shipType), aisShipType: meta.shipType,
      destinationAisReported: stringField(meta.destination, 80),
      longitude, latitude,
      speedKnots: sog !== null && sog >= 0 && sog < 102.3 ? sog : null,
      courseDegrees: cog !== null && cog >= 0 && cog < 360 ? cog : null,
      headingDegrees: heading !== null && heading >= 0 && heading < 360 ? heading : null,
      navigationStatusCode: Number.isInteger(p.navStat) && p.navStat >= 0 && p.navStat <= 15 ? p.navStat : null,
      positionReportedAt: utc(time), metadataReportedAt: utc(meta.timestamp),
    };
    const prev = vessels.get(id);
    if (!prev || prev.positionReportedAt < observation.positionReportedAt) vessels.set(id, observation);
  }
  const out = [...vessels.values()].sort((a,b)=>b.positionReportedAt.localeCompare(a.positionReportedAt)).slice(0,MAX_PUBLIC_ROWS);
  if (out.length === 0) throw Error('no_fresh_commercial_positions');
  return {
    schemaVersion: 1, sourceId: 'fintraffic-ais-v1', provider: 'Fintraffic Digitraffic',
    sourceUrl: API+'locations', metadataSourceUrl: API+'vessels',
    license: 'CC BY 4.0', licenseUrl: LICENSE, termsUrl: TERMS,
    attribution: 'Source: Fintraffic / digitraffic.fi, CC BY 4.0; Stockwatch filters source data for freshness and commercial vessel classes.',
    coverage: 'Finnish AIS receiver network only; not global or fleet-complete',
    method: 'One scheduled snapshot; no interpolated tracks, cargo, operator, confirmed ETA or charter rates',
    retrievedAt: utc(nowMs), maxPositionAgeMinutes: 30, positions: out,
    sourceCount: locations.features.length, metadataCount: metadata.length,
    positionCount: out.length, sourceStatus: 'ok',
  };
}

export async function boundedJson(url, fetcher = fetch, maxBytes = MAX_FETCH_BYTES) {
  if (url !== API+'locations' && url !== API+'vessels') throw Error('upstream_not_allowlisted');
  const response = await fetcher(url, {headers:{
    'Accept':'application/json','Digitraffic-User':'Nordl Stockwatch Maritime Intelligence/1.0 (+https://stocks.nordl.dev)'
  }, redirect:'error', signal:AbortSignal.timeout(15000)});
  if (!response.ok) throw Error(response.status === 429 ? 'upstream_rate_limited' : 'upstream_http_'+response.status);
  const size = Number(response.headers.get('content-length') || 0);
  if (size > maxBytes) throw Error('upstream_too_large');
  if (!response.body) throw Error('upstream_empty_body');
  const reader = response.body.getReader();
  let total = 0;
  const chunks = [];
  try {
    while (true) {
      const {done,value} = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > maxBytes) throw Error('upstream_too_large');
      chunks.push(value);
    }
  } finally { await reader.cancel().catch(()=>{}); }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const part of chunks) {bytes.set(part,offset);offset += part.length;}
  try {return JSON.parse(new TextDecoder().decode(bytes));}
  catch {throw Error('upstream_invalid_json');}
}

async function readObject(bucket,key) {
  const object = await bucket.get(key);
  if (!object) return null;
  try {return await object.json();} catch {return null;}
}
async function writeObject(bucket,key,payload) {
  await bucket.put(key,JSON.stringify(payload),{httpMetadata:{contentType:'application/json'}});
}

export async function collectFintraffic(env,{nowMs=Date.now(),fetcher=fetch}={}) {
  if (env.COLLECTOR_ENABLED !== 'true') return {status:'disabled'};
  if (!env.AIS_BUCKET) throw Error('missing_ais_bucket');
  const prior = await readObject(env.AIS_BUCKET,SNAP);
  const prevTime = prior ? Date.parse(prior.retrievedAt) : NaN;
  if (Number.isFinite(prevTime) && nowMs - prevTime < MIN_FETCH_INTERVAL)
    return {status:'too_recent',retrievedAt:prior.retrievedAt};
  try {
    const locations = await boundedJson(API+'locations',fetcher,6*1024*1024);
    const metadata = await boundedJson(API+'vessels',fetcher,MAX_FETCH_BYTES);
    const result = normalizeFintraffic(locations,metadata,nowMs);
    // Sparse or partial upstream responses cannot erase a normally populated map.
    if (prior?.positionCount >= 40 && result.positionCount < Math.ceil(prior.positionCount/4))
      throw Error('unexpected_source_coverage_collapse');
    await writeObject(env.AIS_BUCKET,SNAP,result);
    await writeObject(env.AIS_BUCKET,HEALTH,{
      status:'ok',lastAttemptAt:utc(nowMs),lastSuccessAt:utc(nowMs),
      positionCount:result.positionCount,sourceId:result.sourceId
    });
    return {status:'ok',positionCount:result.positionCount};
  } catch (error) {
    const reason = String(error?.message || 'source_failure').slice(0,100);
    try {await writeObject(env.AIS_BUCKET,HEALTH,{
      status:'source_error',reason,lastAttemptAt:utc(nowMs),
      lastSuccessAt:prior?.retrievedAt || null,
      lastKnownPositionCount:prior?.positionCount || 0
    });} catch { /* Do not mask original failure */ }
    return {status:'source_error',reason};
  }
}

function serve(data,status=200) {
  return new Response(JSON.stringify(data), {status,headers:{
    'content-type':'application/json; charset=utf-8',
    'cache-control':'public, max-age=30',
    'access-control-allow-origin':FRONTEND,
    'vary':'Origin',
    'x-content-type-options':'nosniff'
  }});
}

export async function getPublicSnapshot(env,nowMs=Date.now()) {
  if (env.PUBLIC_AIS_ENABLED !== 'true') return serve({status:'not_enabled',positions:[]},503);
  if (!env.AIS_BUCKET) return serve({status:'unconfigured',positions:[]},503);
  const latest = await readObject(env.AIS_BUCKET,SNAP);
  const health = await readObject(env.AIS_BUCKET,HEALTH);
  if (!latest || latest.sourceId !== 'fintraffic-ais-v1' || !Array.isArray(latest.positions))
    return serve({status:'not_collected',positions:[]},503);
  const ageMs = nowMs - Date.parse(latest.retrievedAt);
  if (!Number.isFinite(ageMs) || ageMs < -MAX_FUTURE_MS || ageMs > MAX_SNAPSHOT_AGE)
    return serve({status:'stale_snapshot',retrievedAt:latest.retrievedAt,positions:[]},503);
  // Do not show a delayed ship at its old location after position freshness expires.
  const fresh = latest.positions.filter(x => {
    const age = nowMs-Date.parse(x.positionReportedAt);
    return Number.isFinite(age) && age >= -MAX_FUTURE_MS && age <= MAX_POSITION_AGE;
  });
  return serve({...latest,sourceStatus:health?.status || 'unknown',positionCount:fresh.length,
    snapshotAgeSeconds:Math.max(0,Math.round(ageMs/1000)),positions:fresh});
}

export default {
  async fetch(request,env) {
    const path = new URL(request.url).pathname;
    if (request.method !== 'GET') return serve({status:'method_not_allowed'},405);
    if (path === '/api/marine/vessels') return getPublicSnapshot(env);
    if (path === '/api/marine/health') {
      const health = env.AIS_BUCKET ? await readObject(env.AIS_BUCKET,HEALTH) : null;
      return serve({collectorEnabled:env.COLLECTOR_ENABLED==='true',
        publicEnabled:env.PUBLIC_AIS_ENABLED==='true',
        source:'Fintraffic Digitraffic',status:health?.status||'not_collected',
        lastSuccessAt:health?.lastSuccessAt||null,positionCount:health?.positionCount||0});
    }
    return serve({status:'not_found'},404);
  },
  async scheduled(event,env,ctx) {
    ctx.waitUntil(collectFintraffic(env).then(result => {if(result.status === 'source_error')throw Error('ais_collector_source_error');}));
  },
};