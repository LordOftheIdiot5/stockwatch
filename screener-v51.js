/* Same-session market screening. Reference records are not market observations. */
(function(global){'use strict';
const num=x=>typeof x==='number'&&Number.isFinite(x);
const sessionOK=d=>typeof d==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d))&&new Date(d).toISOString().slice(0,10)===d;
function comparable(r,session){return !!(r&&sessionOK(session)&&!r.referenceOnly&&!r.unavailable&&r.date===session&&num(r.close)&&r.close>0&&num(r.changePct)&&num(r.volume)&&r.volume>0)}
function metric(r,key,session){if(key==='volatility')return !r.referenceOnly&&num(r.annualVolPct)?r.annualVolPct:null;if(!comparable(r,session))return null;if(key==='volume')return !r.thin&&num(r.rvol)?r.rvol:null;return key==='abs'?Math.abs(r.changePct):r.changePct}
function rank(rows,key,session){const name=(a,b)=>String(a.name||a.ticker).localeCompare(String(b.name||b.ticker))||String(a.ticker).localeCompare(String(b.ticker));return [...rows].sort((a,b)=>{if(key==='name')return name(a,b);const x=metric(a,key,session),y=metric(b,key,session);if(x===null||y===null)return x===y?name(a,b):x===null?1:-1;return (key==='loss'?x-y:y-x)||name(a,b)})}
function filters(rows,{session,currency='all',coverage='all'}={}){return rows.filter(r=>(currency==='all'||r.currency===currency)&&(coverage==='all'||(coverage==='comparable'?comparable(r,session):coverage==='missing'?!comparable(r,session):true)))}
function heatValue(r,key,session){return metric(r,key==='volume'?'volume':'gain',session)}
const api={comparable,metric,rank,filters,heatValue};if(typeof module==='object'&&module.exports)module.exports=api;else global.StockwatchScreener=api;
})(typeof window!=='undefined'?window:{});
