/* Same-session market screening. Reference records are not market observations. */
(function(global){'use strict';
const num=x=>typeof x==='number'&&Number.isFinite(x);
const sessionOK=d=>typeof d==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d))&&new Date(d).toISOString().slice(0,10)===d;
function comparisonDate(snapshot,now=Date.now()){const t=Date.parse(snapshot);if(!Number.isFinite(t))return null;const d=new Date(Math.max(t,now));if(d.getUTCHours()<22)d.setUTCDate(d.getUTCDate()-1);while(d.getUTCDay()===0||d.getUTCDay()===6)d.setUTCDate(d.getUTCDate()-1);return d.toISOString().slice(0,10)}
function hasPrice(r){return !!(r&&!r.referenceOnly&&!r.unavailable&&num(r.close)&&r.close>0&&sessionOK(r.date)&&typeof r.currency==='string'&&r.currency.length>0)}
// Pair observations are already published in the A/B research view. They are
// display-only, not scanner bars or independently verified active listings.
const pairListings={
 'XCSE:MAERSK A':'MAERSK-A.CO','XCSE:MAERSK B':'MAERSK-B.CO',
 'XSTO:ATCO A':'ATCO-A.ST','XSTO:ATCO B':'ATCO-B.ST',
 'XSTO:ERIC A':'ERIC-A.ST','XSTO:ERIC B':'ERIC-B.ST',
 'XSTO:SKF A':'SKF-A.ST','XSTO:SKF B':'SKF-B.ST'
};
// Explicit venue + FIGI + share-class ticker bindings; no fuzzy name matches.
const expandedPairListings={
 'BBG000BB48H2':['HUSQB','HUSQ-B.ST'],
 'BBG000BG96K6':['INVEA','INVE-A.ST'],
 'BBG000BCH127':['VOLVA','VOLV-A.ST'],
 'BBG000BGD8Q1':['SSABB','SSAB-B.ST'],
 'BBG000BB28Z4':['HUSQA','HUSQ-A.ST']
};
function pairDailyMove(move,day){
 if(!move||move.method!=='individual_daily_closes'||move.date!==day||!sessionOK(day)||!sessionOK(move.previousDate)||!num(move.changePct)||move.changePct < -100)return null;
 const prev=new Date(day);if(prev.getUTCDay()===0||prev.getUTCDay()===6)return null;
 prev.setUTCDate(prev.getUTCDate()-1);while(prev.getUTCDay()===0||prev.getUTCDay()===6)prev.setUTCDate(prev.getUTCDate()-1);
 if(prev.toISOString().slice(0,10)!==move.previousDate)return null;
 return {date:day,previousDate:move.previousDate,changePct:move.changePct,method:move.method};
}
function pairQuote(r,pairs){
 if(!r?.referenceOnly)return null;
 let ticker=null;
 if(r.referenceId&&r.referenceId===r.mic+':'+r.symbol)ticker=pairListings[r.referenceId];
 else if(r.expandedReference===true&&r.registryOnly===true&&r.mic==='XSTO'&&r.ticker==='registry:XSTO:'+r.figi){
  const m=expandedPairListings[r.figi];if(m&&m[0]===r.symbol)ticker=m[1];
 }
 const currency=r.mic==='XCSE'?'DKK':r.mic==='XSTO'?'SEK':null;
 if(!ticker||!currency)return null;
 const matches=(pairs||[]).filter(p=>p.currency===currency&&sessionOK(p.priceDate)&&((p.a===ticker&&num(p.aPrice)&&p.aPrice>0)||(p.b===ticker&&num(p.bPrice)&&p.bPrice>0)));
 if(matches.length!==1)return null;
 const p=matches[0];
 const move=pairDailyMove(p.a===ticker?p.aDailyMove:p.bDailyMove,p.priceDate);
 return {close:p.a===ticker?p.aPrice:p.bPrice,date:p.priceDate,currency,source:'Existing A/B research observation',ticker,...(move?{dailyMove:move}:{}),...(p.observationStatus==='retained'?{retained:true}:{})};
}
function displayPrice(r){return hasPrice(r)?{close:r.close,date:r.date,currency:r.currency,source:'Scanner observation'}:r?.pairQuote||null}
function latestChange(r){return hasPrice(r)&&num(r.volume)&&r.volume>0&&num(r.changePct)?r.changePct:null}
function comparable(r,session){return !!(r&&sessionOK(session)&&!r.referenceOnly&&!r.unavailable&&r.priceStatus!=='retained'&&r.date===session&&num(r.close)&&r.close>0&&num(r.changePct)&&num(r.volume)&&r.volume>0)}
function metric(r,key,session){if(key==='volatility')return !r.referenceOnly&&num(r.annualVolPct)?r.annualVolPct:null;if(!comparable(r,session))return null;if(key==='volume')return !r.thin&&num(r.rvol)?r.rvol:null;return key==='abs'?Math.abs(r.changePct):r.changePct}
function rank(rows,key,session){const name=(a,b)=>String(a.name||a.ticker).localeCompare(String(b.name||b.ticker))||String(a.ticker).localeCompare(String(b.ticker));return [...rows].sort((a,b)=>{if(key==='name')return name(a,b);const x=metric(a,key,session),y=metric(b,key,session);if(x===null||y===null)return x===y?(Number(!!displayPrice(b))-Number(!!displayPrice(a))||name(a,b)):x===null?1:-1;return (key==='loss'?x-y:y-x)||name(a,b)})}
function filters(rows,{session,currency='all',coverage='all'}={}){return rows.filter(r=>(currency==='all'||r.currency===currency)&&(coverage==='all'||(coverage==='comparable'?comparable(r,session):coverage==='missing'?!comparable(r,session):true)))}
function heatValue(r,key,session){return metric(r,key==='volume'?'volume':'gain',session)}
const api={pairQuote,displayPrice,hasPrice,latestChange,comparisonDate,comparable,metric,rank,filters,heatValue};if(typeof module==='object'&&module.exports)module.exports=api;else global.StockwatchScreener=api;
})(typeof window!=='undefined'?window:{});
