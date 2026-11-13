// Stockwatch read-only historical news endpoint and authenticated ingestion for Cloudflare D1.
// Bind D1 database as DB and an independent random NEWS_INGEST_TOKEN secret.
const cors={'Access-Control-Allow-Origin':'https://stocks.nordl.dev','Vary':'Origin','Access-Control-Allow-Methods':'GET,OPTIONS','Access-Control-Allow-Headers':'Content-Type,Authorization'};
const json=(data,status=200)=>new Response(JSON.stringify(data),{status,headers:{...cors,'content-type':'application/json; charset=utf-8','cache-control':'no-store'}});
const isHttps=u=>{try{return new URL(u).protocol==='https:'}catch{return false}};
const validItem=x=>x&&typeof x.id==='string'&&x.id.length>0&&x.id.length<=512&&typeof x.ticker==='string'&&x.ticker.length>0&&x.ticker.length<=40&&typeof x.headline==='string'&&x.headline.length>0&&x.headline.length<=1200&&['news','disclosure'].includes(x.type)&&typeof x.url==='string'&&x.url.length<=2048&&isHttps(x.url)&&Number.isFinite(Date.parse(x.published))&&(!x.match||['unverified','name_mentioned','issuer_code'].includes(x.match))&&(!x.name||(typeof x.name==='string'&&x.name.length<=200))&&(!x.sector||(typeof x.sector==='string'&&x.sector.length<=100))&&(!x.publisher||(typeof x.publisher==='string'&&x.publisher.length<=200))&&(!x.english||(typeof x.english==='string'&&x.english.length<=1200))&&(!x.lang||(typeof x.lang==='string'&&x.lang.length<=16));
export default {async fetch(request,env){const url=new URL(request.url);const path=url.pathname;
 if(request.method==='OPTIONS')return new Response(null,{status:204,headers:cors});
 if(path==='/api/health'&&request.method==='GET'){
  if(!env.DB)return json({status:'unconfigured',storage:'d1'},503);
  try {const row=await env.DB.prepare('SELECT COUNT(*) AS articles FROM news_items').first();return json({status:'ok',storage:'d1',articles:Number(row?.articles||0)});}
  catch{return json({status:'database_error',storage:'d1'},503)}
 }
 if(!env.DB)return json({error:'database_not_bound'},503);
 if(path==='/api/news'&&request.method==='GET'){
  const limit=Math.min(100,Math.max(1,+url.searchParams.get('limit')||50));
  const ticker=(url.searchParams.get('ticker')||'').trim().slice(0,40),kind=url.searchParams.get('type')||'',before=url.searchParams.get('before')||'',sector=(url.searchParams.get('sector')||'').trim().slice(0,100);
  if(kind&&!['news','disclosure'].includes(kind))return json({error:'invalid_type'},400);
  if(before&&!/^20\d\d-\d\d-\d\d(?:T[0-9:]+Z)?$/.test(before))return json({error:'invalid_before'},400);
  let sql='SELECT id,ticker,company_name AS name,sector,kind AS type,headline,original_language AS lang,translated_headline AS english,publisher,original_url AS url,published_at AS published,source_match AS match,regulatory FROM news_items WHERE 1=1';const args=[];
  if(ticker){sql+=' AND ticker=?';args.push(ticker)}if(sector){sql+=' AND sector=?';args.push(sector)}if(kind){sql+=' AND kind=?';args.push(kind)}if(before){sql+=' AND published_at<?';args.push(before)}sql+=' ORDER BY published_at DESC,id DESC LIMIT ?';args.push(limit);
  const out=await env.DB.prepare(sql).bind(...args).all();return json({items:out.results||[],count:out.results?.length||0,limit});
 }
 if(path==='/api/news/ingest'&&request.method==='POST'){
  // Token configured only as a Worker secret, never in client-facing HTML or logs.
  const secret=String(env.NEWS_INGEST_TOKEN||'').replace(/^\uFEFF+/, '').trim();if(!secret)return json({error:'not_configured'},503);
  const authorization=request.headers.get('authorization')||'';if(authorization!==`Bearer ${secret}`)return json({error:'forbidden'},403);
  if(+(request.headers.get('content-length')||0)>450000)return json({error:'too_large'},413);
  let payload;try{const raw=await request.text();if(new TextEncoder().encode(raw).length>450000)return json({error:'too_large'},413);payload=JSON.parse(raw)}catch{return json({error:'invalid_json'},400)}
  if(!payload||!Array.isArray(payload.items)||payload.items.length>150||payload.items.some(x=>!validItem(x)))return json({error:'invalid_items'},400);
  const recorded=new Date().toISOString();const q=`INSERT INTO news_items (id,ticker,company_name,sector,kind,headline,original_language,translated_headline,publisher,original_url,published_at,recorded_at,source_match,regulatory) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET source_match=excluded.source_match WHERE source_match='unverified' AND excluded.source_match!='unverified'`;
  const stmts=payload.items.map(x=>env.DB.prepare(q).bind(x.id,x.ticker,x.name||x.ticker,x.sector||'',x.type,x.headline,x.lang||'',x.english||'',x.publisher||'',x.url,new Date(x.published).toISOString(),recorded,x.match||'unverified',x.regulatory?1:0));
  for(let i=0;i<stmts.length;i+=50)await env.DB.batch(stmts.slice(i,i+50));return json({accepted:stmts.length});
 }
 return json({error:'not_found'},404)
}};
