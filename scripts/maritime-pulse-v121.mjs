/* V121 Maritime Market Pulse — deterministic, evidence-only comparisons.
 * These are changes within each original provider's series, NOT daily
 * maritime quotes, market causes, forecasts, trading alerts or ship activity.
 * All figures are computed from existing public Stockwatch source snapshots.
 */
const finite = x => typeof x === 'number' && Number.isFinite(x);
const round1 = x => Math.round((x + Number.EPSILON) * 10) / 10;
const asPercent = (current, previous) =>
  finite(current) && finite(previous) && previous > 0 ? round1((current / previous - 1) * 100) : null;
const isoDay = x => typeof x === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(x) && !Number.isNaN(Date.parse(x)) ? x : null;
const monthNum = x => typeof x === 'string' && /^\d{4}-\d{2}$/.test(x) ? Number(x.slice(0,4))*12 + Number(x.slice(5,7)) : NaN;
const quarterNum = x => typeof x === 'string' && /^\d{4}-Q[1-4]$/.test(x) ? Number(x.slice(0,4))*4 + Number(x.slice(-1)) : NaN;
const yesterdayOrBefore = (x,now) => {
  const date = isoDay(x);
  return !!date && Date.parse(date) <= now.getTime() + 86400000;
};
const validSource = s => typeof s === 'string' && /^https:\/\/[A-Za-z0-9._-]+\/[^ ]+/.test(s);
const seriesBy = (root,key) => Array.isArray(root?.series) ? root.series.find(x=>x?.key===key) : null;
const companySeries = (root,ticker,key) => Array.isArray(root?.companies) ?
  root.companies.find(x=>x?.ticker===ticker)?.series?.find(x=>x.key===key) : null;
const entry = (history,i) => {
  const x=history?.[i]; return x && finite(x.value) ? x : null;
};
function lastTwo(series,mode,now){
 if(!series||!Array.isArray(series.history)||series.history.length<2)return null;
 const h=series.history, a=entry(h,h.length-1),b=entry(h,h.length-2);
 if(!a||!b)return null;
 const aDate=isoDay(a.date),bDate=isoDay(b.date);
 if(!aDate||!bDate||!yesterdayOrBefore(aDate,now))return null;
 if(mode==='weekly'&&Date.parse(aDate)-Date.parse(bDate)!==7*86400000)return null;
 if(mode==='monthly'&&monthNum(aDate.slice(0,7))-monthNum(bDate.slice(0,7))!==1)return null;
 if(mode==='annual'&&Number(aDate.slice(0,4))-Number(bDate.slice(0,4))!==1)return null;
 return {a,b};
}
function yearOnYearQuarter(series,now){
 const h=series?.history;
 if(!Array.isArray(h)||!h.length)return null;
 const a=entry(h,h.length-1);
 if(!a||!Number.isFinite(quarterNum(a.period)))return null;
 const asOf=String(a.period).slice(0,4);
 if(Number(asOf)>now.getUTCFullYear())return null;
 const previous=String(Number(asOf)-1)+'-'+String(a.period).slice(5);
 const b=h.find(x=>x?.period===previous&&finite(x.value));
 return b ? {a,b}:null;
}
function recentCompany(company,now){
 const h=company?.observations;
 if(!Array.isArray(h)||h.length<2)return null;
 const a=h[h.length-1],b=h[h.length-2];
 if(!finite(a?.value)||!finite(b?.value)||!yesterdayOrBefore(a.periodEnd,now))return null;
 const ma=monthNum(a.periodEnd?.slice(0,7)),mb=monthNum(b.periodEnd?.slice(0,7));
 if(!Number.isFinite(ma)||ma-mb!==3)return null;
 return {a,b};
}
function observationCurrentEnough(period,frequency,now){
 let end;
 if(frequency==='weekly')end=Date.parse(period);
 else if(frequency==='monthly'&&/^\d{4}-\d{2}$/.test(period)){
  const y=Number(period.slice(0,4)),m=Number(period.slice(5,7));
  if(m<1||m>12)return false;
  end=Date.UTC(y,m,0);
 }else if(frequency==='quarterly'&&/^\d{4}-Q[1-4]$/.test(period)){
  end=Date.UTC(Number(period.slice(0,4)),Number(period.slice(-1))*3,0);
 }else if(frequency==='issuer'&&isoDay(period))end=Date.parse(period);
 else if(frequency==='annual'&&/^\d{4}$/.test(period))end=Date.UTC(Number(period),11,31);
 else return false;
 const age=(now.getTime()-end)/86400000;
 const limit={weekly:30,monthly:150,quarterly:270,issuer:210,annual:1095}[frequency];
 return Number.isFinite(age)&&age>=-2&&age<=limit;
}
function valuePercent(x){return x===null?null:(x>0?'+':'')+x.toFixed(1)+'%'}
const item=(label,pair,period,unit,frequency,description) => ({
 label,period,unit,frequency,description,
 value:pair.a.value,previous:pair.b.value,changePct:asPercent(pair.a.value,pair.b.value)
});
function baseSignal(id,type,title,period,headline,caveat,source,sourceUrl,scope,figures,extra={}){
 if(!figures.length||!validSource(sourceUrl)||figures.some(f=>f.changePct===null))return null;
 return {
  schemaVersion:1,id,type,kind:'observed_comparison',title,period,headline,caveat,
  source,sourceUrl,scope,figures,review:'Observed source data; interpretation is not a causal or investment claim',
  ...extra
 };
}
/* Never compare a quarter with a different quarter's seasonal pattern,
 * two different issuer scopes, or incompatible freight price units.
 * Per-source cards may be absent; never fabricate an empty replacement. */
export function buildMaritimePulse(data,{now=new Date()}={}){
 if(!(now instanceof Date)||!Number.isFinite(now.getTime()))throw Error('invalid_pulse_clock');
 const signals=[],diagnostics=[];
 const add=(value,why)=>value?signals.push(value):diagnostics.push(why);
 const freight=data?.freight;
 const gf=seriesBy(freight,'usda:gulf-japan-index');
 const pf=seriesBy(freight,'usda:pnw-japan-index');
 const ga=lastTwo(gf,'weekly',now),pa=lastTwo(pf,'weekly',now);
 add(ga&&pa&&observationCurrentEnough(ga.a.date,'weekly',now)&&ga.a.date===pa.a.date&&gf.period===ga.a.date&&pf.period===pa.a.date&&
  baseSignal('usda-grain-week','ocean_cost','Ocean grain costs: Gulf eased, Pacific Northwest steady',
   ga.a.date,'Two USDA ocean freight cost indices, compared with the preceding week.',
   '2017=100 indices, not USD/tonne prices or Baltic Exchange freight assessments.',
   'USDA Agricultural Marketing Service',gf?.sourceUrl,'U.S. Gulf and Pacific Northwest routes to Japan',
   [item('U.S. Gulf → Japan',ga,ga.a.date,gf.unit,'weekly','Index'),
    item('Pacific Northwest → Japan',pa,pa.a.date,pf.unit,'weekly','Index')],
   {snapshotAt:freight?.generated,comparison:'previous_week',
    investigation:'Review the next dated USDA report and whether both route indices move together. This is not evidence of daily charter earnings.',
    focus:{layer:'lanes'}}),'usda_weekly_unavailable_or_period_mismatch');
 const conn=data?.connectivity;const markets=[
  ['denmark','Denmark'],['sweden','Sweden'],['norway','Norway']
 ].map(([slug,label])=>({label,s:seriesBy(conn,'unctad:lsci-monthly:'+slug)}));
 const pairs=markets.map(x=>({...x,p: lastTwo(x.s,'monthly',now)}));
 add(pairs.every(x=>x.p&&x.s.period===x.p.a.date.slice(0,7)&&observationCurrentEnough(x.s.period,'monthly',now))&&
     pairs.every(x=>x.s.period===pairs[0].s.period)&&
  baseSignal('nordic-liner-network','liner_connectivity','Nordic liner networks diverged',
   pairs[0]?.s?.period||'',
   'Denmark and Sweden weakened month over month, while Norway improved.',
   'Country-level scheduled-service network connectivity. Not a vessel position, cargo count, freight price or bookings measure.',
   'UN Trade and Development (UNCTAD)',conn?.source?.sourceUrl,'Denmark, Sweden and Norway',
   pairs.map(x=>item(x.label,x.p,x.s.period,x.s.unit,'monthly','Connectivity index')),
   {snapshotAt:conn?.generated,comparison:'previous_month',
    investigation:'Compare future port-level service connectivity or verified port calls before proposing a cause or a change in cargo demand.',
     focus:{lon:12,lat:57,width:185}}),'unctad_monthly_unavailable_or_period_mismatch');
 const ro=data?.roro;const qs=[
  ['NO','Norway'],['SE','Sweden'],['NL','Netherlands']
 ].map(([code,label])=>({label,s:ro?.series?.find(x=>x?.countryCode===code)}));
 const q=qs.map(x=>({...x,p:yearOnYearQuarter(x.s,now)}));
 add(q.every(x=>x.p&&x.s.period===q[0].s.period&&observationCurrentEnough(x.s.period,'quarterly',now))&&
  baseSignal('nordic-roro-yoy','roro_cargo','Ro-Ro volumes rose in Norway, Sweden and the Netherlands',
   q[0]?.s?.period||'',
   'Published main-port Ro-Ro gross cargo weight increased versus the same quarter a year earlier.',
   'Country totals in thousand tonnes, not vessel utilization, vehicle exports or freight rates. EU aggregate overlaps country totals and is not added.',
   'Eurostat',ro?.sourceUrl,'Norway, Sweden and Netherlands',
   q.map(x=>item(x.label,x.p,x.s.period,x.s.unit,'quarterly','Same quarter last year')),
   {snapshotAt:ro?.observedOn,comparison:'same_quarter_prior_year',
    investigation:'Check later same-quarter cargo reports and issuer-specific volume disclosures. The country aggregate does not reveal which carrier benefited.',
     focus:{lon:10,lat:58,width:170}}),'eurostat_roro_yoy_unavailable');
 const ports=data?.ports;const goods=[
  ['WLD','World'],['VNM','Viet Nam'],['NOR','Norway']
 ].map(([code,label])=>({label,s:ports?.series?.find(x=>x?.countryCode===code)}));
 const g=goods.map(x=>({...x,p:lastTwo(x.s,'annual',now)}));
 add(g.every(x=>x.p&&x.s.period===g[0].s.period&&observationCurrentEnough(x.s.period,'annual',now))&&
  baseSignal('global-container-history','container_handling','Global container handling expanded in 2024',
   g[0]?.s?.period||'',
   'World and selected country annual container throughput changed differently.',
   'Historical country/global totals, not current-day throughput, individual port totals or demand forecasts. Country totals are included in the world total.',
   'World Bank WDI (UNCTAD-origin)',ports?.source?.sourceUrl,'World, Viet Nam and Norway',
   g.map(x=>item(x.label,x.p,x.s.period,'TEU','annual','Container handling')),
   {snapshotAt:ports?.generated,comparison:'prior_year',historical:true,
    investigation:'Use this long-run baseline alongside newer port statistics when available; 2024 data cannot describe current vessel demand.',
     focus:{preset:'world'}}),'worldbank_annual_comparison_unavailable');
 const metrics=data?.company;
 const issued=[
  ['net_freight','Realized net freight'],
  ['transport_volume','Transported cargo volume'],
  ['backlog','Contract backlog']
 ].map(([key,label])=>({label,p:recentCompany(companySeries(metrics,'WAWI.OL',key),now),
       key,metric:companySeries(metrics,'WAWI.OL',key)}));
 const m=issued.map(x=>({...x,period:x.p?.a?.periodEnd?.slice(0,7)}));
 const companyRoot=Array.isArray(metrics?.companies)?metrics.companies.find(x=>x.ticker==='WAWI.OL'):null;
 const source=m[0]?.p?.a?.sourceUrl;
 add(m.every(x=>x.p&&x.period===m[0].period&&x.p.a.periodEnd===m[0].p.a.periodEnd&&observationCurrentEnough(x.p.a.periodEnd,'issuer',now))&&
  baseSignal('wallenius-operations','issuer_operating','Wallenius Wilhelmsen reported mixed operating changes',
   m[0]?.p?.a?.periodEnd||'',
   'Q3 realized net freight rose, while transported volume and contract backlog declined versus Q2.',
   'Issuer-specific realized figures; not broker spot rates, verified cash flows or a forecast of next-quarter earnings.',
   'Wallenius Wilhelmsen ASA',source,'Wallenius Wilhelmsen (WAWI.OL)',
   m.map(x=>item(x.label,x.p,x.p.a.periodEnd,x.metric.unit,'quarterly','Company filing')),
   {snapshotAt:metrics?.compiledOn,comparison:'prior_quarter',
    investigation:'Follow subsequent company releases for backlog, transported volumes and realized freight; the disclosed mix does not determine the next stock move.',
     companyUrl:'company.html?ticker=WAWI.OL'}),'issuer_comparable_operating_metrics_unavailable');
 const rates=data?.rates;const quotes=rates?.rates||[];
 const gulf=quotes.find(x=>x.id?.startsWith('us-gulf-japan')&&finite(x.value));
 const pnw=quotes.find(x=>x.id?.startsWith('pnw-japan')&&finite(x.value));
 if(gulf&&pnw&&gulf.observationDate===pnw.observationDate&&rates.isBrokerRate===false&&
   validSource(rates.sourceUrl)&&yesterdayOrBefore(gulf.observationDate,now)&&observationCurrentEnough(gulf.observationDate,'weekly',now)){
  signals.push({schemaVersion:1,id:'usda-grain-indications',kind:'observed_levels',type:'freight_indications',
   title:'USDA reported grain freight indications for two routes',
   period:gulf.observationDate,scope:'U.S. Gulf / Pacific Northwest → Japan',
   headline:'Two original government-published route observations; not a trend or an executable quotation.',
   caveat:'Routes have different origins and distances. Do not treat their price gap as a trading arbitrage, ship earnings, or a time-series change.',
   source:'USDA Agricultural Marketing Service',sourceUrl:rates.sourceUrl,
   snapshotAt:rates.reportedAt,figures:[{label:'U.S. Gulf → Japan',value:gulf.value,unit:'USD/metric tonne',period:gulf.observationDate},
    {label:'Pacific Northwest → Japan',value:pnw.value,unit:'USD/metric tonne',period:pnw.observationDate}],
   review:'Source-dated levels only; no equivalent previous rates provided',
   investigation:'Compare the next original USDA route report before inferring any directional change; route distances and conditions differ.',
   focus:{layer:'lanes'}});
 }else diagnostics.push('usda_source_dated_route_indications_unavailable');
 const cadence={weekly:'weekly',monthly:'monthly',quarterly:'quarterly',annual:'annual'};
 return {schemaVersion:1,generatedAt:now.toISOString(),status:signals.length?'source_backed':'no_verified_comparisons',
  signalCount:signals.length,signals,missing:diagnostics,
  methodology:'Original periods and source URLs must be preserved. Changes are arithmetic comparisons within one compatible series; absence of data is not zero. No causality, prediction or licensed spot quote is inferred.',
  blocked:['daily Baltic route prices','live vessel positions','port-level cargo flow and arrivals','verified company sensitivity or forward earnings']};
}
export {asPercent,valuePercent};
