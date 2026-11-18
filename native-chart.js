/* Stockwatch V49 native chart core. No external script, synthetic price feed or network access. */
(function(global){
'use strict';
const A=typeof module==='object'&&module.exports?require('./research-analytics.js'):global.StockwatchAnalytics;
const num=x=>typeof x==='number'&&Number.isFinite(x);
const dateOK=x=>typeof x==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(x)&&Number.isFinite(Date.parse(x))&&new Date(x).toISOString().slice(0,10)===x;
const safe=u=>{try{return new URL(u).protocol==='https:'&&!!new URL(u).hostname}catch{return false}};
const E=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const F=n=>num(n)?n.toLocaleString('en-GB',{maximumFractionDigits:4}):'—';
function cleanBars(rows){
 const m=new Map(),bad=new Set();
 for(const b of Array.isArray(rows)?rows:[]){
  if(!b||!dateOK(b.date)||!num(b.close)||b.close<=0)continue;
  const v={date:b.date,close:b.close};
  if([b.open,b.high,b.low].every(x=>num(x)&&x>0)&&b.high>=Math.max(b.open,b.close,b.low)&&b.low<=Math.min(b.open,b.close))Object.assign(v,{open:b.open,high:b.high,low:b.low});
  if(Number.isSafeInteger(b.volume)&&b.volume>=0)v.volume=b.volume;
  if(m.has(b.date)&&JSON.stringify(m.get(b.date))!==JSON.stringify(v))bad.add(b.date);else m.set(b.date,v);
 }
 return [...m].filter(([d])=>!bad.has(d)).sort(([d],[e])=>d.localeCompare(e)).map(([,b])=>b);
}
function authorized(entry,payload){
 return !!(entry&&payload&&entry.redistributionPermitted===true&&payload.redistributionPermitted===true&&entry.priceType==='end_of_day'&&payload.priceType==='end_of_day'&&/^data\/licensed-reference-history\/[a-f0-9]{32}\.json$/.test(entry.historyPath||'')&&['listingId','currency','source','licenseReference'].every(k=>typeof entry[k]==='string'&&entry[k]&&entry[k]===payload[k])&&safe(payload.licenseReference)&&safe(payload.sourceUrl)&&typeof payload.adjusted==='boolean'&&(entry.adjusted===undefined||entry.adjusted===payload.adjusted));
}
function mount(host,{label='',unit='',bars=[],series=[],equity=false,source='',notice='',events=[],onReset=null,onChange=null}={}){
 const b=equity?cleanBars(bars):[];
 const sets=equity?[{label,points:b.map(x=>({date:x.date,value:x.close}))}]:series.map(x=>({...x,points:A.clean(x.points)})).filter(x=>x.points.length);
 const dates=[...new Set(sets.flatMap(s=>s.points.map(p=>p.date)))].sort();
 const map=new Map(b.map(x=>[x.date,x]));
 const eventMap=new Map();
 if(equity)for(const e of Array.isArray(events)?events:[]){if(!e||!dateOK(e.date)||!map.has(e.date)||!safe(e.url)||typeof e.headline!=='string')continue;const group=eventMap.get(e.date)||[];group.push(e);eventMap.set(e.date,group)}
 const candles=equity&&b.length>1&&b.every(x=>num(x.open)&&num(x.high)&&num(x.low));
 const hasVolume=equity&&b.some(x=>num(x.volume));
 const many=sets.length>1;
 let mode=candles?'candles':'line',range=A.chartWindow(dates.length,0,Math.min(dates.length,180)),cursor=range.end-1;
 if(dates.length>180)range=A.chartWindow(dates.length,dates.length-180,180);
 let sma=false,ema=false,rsi=false,showVolume=hasVolume,tool='pan',drawings=[],first=null,drag=null;
 const full=sets[0]?.points||[],ind={sma:A.sma(full,20),ema:A.ema(full,20),rsi:A.rsi(full,14)};
 const pointers=new Map();let pinch=null;
 const colors=['#4ce2b5','#8caef8','#ecc37a','#bc83e7','#df7089'];
 host.innerHTML='<div class="sw49-toolbar" role="group" aria-label="Native chart controls"><strong>'+E(label||'Historical observations')+'</strong><button data-act="line" type="button">Line</button><button data-act="candles" type="button" '+(!candles?'disabled title="Genuine OHLC unavailable"':'')+'>Candles</button><button data-act="sma" type="button" '+(many||!ind.sma.length?'disabled':'')+'>SMA 20</button><button data-act="ema" type="button" '+(many||!ind.ema.length?'disabled':'')+'>EMA 20</button><button data-act="rsi" type="button" '+(many||!ind.rsi.length?'disabled':'')+'>RSI 14</button><button data-act="volume" type="button" '+(!hasVolume?'disabled':'')+'>Volume</button><button data-act="in" type="button" aria-label="Zoom in">+</button><button data-act="out" type="button" aria-label="Zoom out">−</button><button data-act="older" type="button" aria-label="Pan earlier">←</button><button data-act="newer" type="button" aria-label="Pan later">→</button><button data-act="reset" type="button">Reset</button></div><div class="sw49-workbench"><div class="sw49-draw" role="group" aria-label="Drawing tools"><button data-act="pan" title="Pan and inspect" aria-label="Pan and inspect" type="button">✥</button><button data-act="trend" title="Draw trend line" aria-label="Draw trend line" type="button" '+(many?'disabled':'')+'>╱</button><button data-act="horizontal" title="Draw horizontal line" aria-label="Draw horizontal line" type="button" '+(many?'disabled':'')+'>─</button><button data-act="clear" title="Remove drawings" aria-label="Remove drawings" type="button">⌫</button></div><div class="sw49-chartstack"><div class="sw49-plot" tabindex="0" aria-label="Chart: arrow keys inspect, plus/minus zoom"></div><div class="sw49-rsi"></div></div></div><div class="sw-terminal-inspector" aria-live="polite"></div><div class="sw-meta" data-chart-events></div><label class="sw-terminal-range">Inspect date <input aria-label="Inspect observation date" type="range" min="0" step="1"></label><div class="sw49-foot"><span data-window></span><span data-tool></span></div><p class="sw-meta">'+E(notice||'Dated observations only; no interpolation or generated bars.')+' '+(safe(source)?'<a href="'+E(source)+'" target="_blank" rel="noopener noreferrer">Source ↗</a>':'')+'</p>';
 const plot=host.querySelector('.sw49-plot'),lower=host.querySelector('.sw49-rsi'),info=host.querySelector('.sw-terminal-inspector'),slider=host.querySelector('input');
 if(dates.length<2){plot.textContent='Insufficient authorized dated observations. No chart values generated.';host.querySelectorAll('button,input').forEach(x=>x.disabled=true);return null}
 const W=900,H=330,L=12,R=80,T=14,B=25,Xend=W-R,priceEnd=()=>showVolume?H-B-66:H-B;
 let geom={},silent=false;
 const active=(k,on)=>{const e=host.querySelector('[data-act="'+k+'"]');e.setAttribute('aria-pressed',String(on));e.classList.toggle('active',on)};
 function paint(){
  cursor=Math.max(range.start,Math.min(range.end-1,cursor));
  const ds=dates.slice(range.start,range.end),dset=new Set(ds),vs=sets.map(s=>({...s,points:s.points.filter(p=>dset.has(p.date))}));
  const lookup=new Map(ds.map((d,i)=>[d,i])),x=d=>L+(lookup.get(d)||0)/(Math.max(1,ds.length-1))*(Xend-L);
  const vals=vs.flatMap(s=>s.points.map(p=>p.value)),vb=ds.map(d=>map.get(d)).filter(Boolean);
  if(mode==='candles')for(const p of vb)vals.push(p.high,p.low);
  if(sma)for(const p of ind.sma)if(dset.has(p.date))vals.push(p.value);
  if(ema)for(const p of ind.ema)if(dset.has(p.date))vals.push(p.value);
  const min=Math.min(...vals),max=Math.max(...vals),pad=Math.max((max-min)*.08,Math.abs(max)*.004,.00001),lo=min-pad,hi=max+pad,pe=priceEnd(),y=v=>T+(hi-v)/(hi-lo)*(pe-T);
  geom={x,y,lo,hi,pe,ds};
  const grid=Array.from({length:5},(_,i)=>{const v=hi-(hi-lo)*i/4;return '<line x1="'+L+'" x2="'+Xend+'" y1="'+y(v)+'" y2="'+y(v)+'" class="sw49-grid"/><text x="'+(Xend+7)+'" y="'+(y(v)+4)+'">'+E(F(v))+'</text>'}).join('');
  const path=(pts,clr)=>{const q=pts.filter(p=>dset.has(p.date));return q.length===1?'<circle cx="'+x(q[0].date)+'" cy="'+y(q[0].value)+'" r="3" fill="'+clr+'"/>':q.length?'<polyline fill="none" stroke="'+clr+'" stroke-width="1.7" vector-effect="non-scaling-stroke" points="'+q.map(p=>x(p.date)+','+y(p.value)).join(' ')+'"/>':''};
  const cw=Math.max(1,Math.min(12,(Xend-L)/ds.length*.7));
  const price=mode==='candles'?vb.map(p=>{const col=p.close>=p.open?'var(--sw-green)':'var(--sw-red)';return '<g data-candle><line x1="'+x(p.date)+'" x2="'+x(p.date)+'" y1="'+y(p.high)+'" y2="'+y(p.low)+'" stroke="'+col+'"/><rect x="'+(x(p.date)-cw/2)+'" y="'+Math.min(y(p.open),y(p.close))+'" width="'+cw+'" height="'+Math.max(1,Math.abs(y(p.open)-y(p.close)))+'" fill="'+col+'"/></g>'}).join(''):vs.map((s,i)=>path(s.points,colors[i%colors.length])).join('');
  const vmax=Math.max(1,...vb.filter(p=>num(p.volume)).map(p=>p.volume));
  const volume=showVolume?vb.filter(p=>num(p.volume)).map(p=>'<rect data-volume x="'+(x(p.date)-cw/2)+'" y="'+(H-B-p.volume/vmax*54)+'" width="'+cw+'" height="'+(p.volume/vmax*54)+'" fill="var(--sw-mint)" opacity=".4"/>').join('')+'<text x="'+(Xend+7)+'" y="'+(H-B-45)+'">Vol.</text>':'';
  const lines=drawings.map(d=>d.kind==='horizontal'?'<line x1="'+L+'" x2="'+Xend+'" y1="'+y(d.a.value)+'" y2="'+y(d.a.value)+'" stroke="#ecc37a" stroke-dasharray="5 3"/>':lookup.has(d.a.date)&&lookup.has(d.b.date)?'<line x1="'+x(d.a.date)+'" x2="'+x(d.b.date)+'" y1="'+y(d.a.value)+'" y2="'+y(d.b.value)+'" stroke="#ecc37a" stroke-width="1.5"/>':'').join('');
  const ticks=[0,Math.floor((ds.length-1)/2),ds.length-1].filter((v,i,arr)=>arr.indexOf(v)===i).map((i)=>'<text x="'+x(ds[i])+'" y="'+(H-7)+'" text-anchor="'+(i===0?'start':i===ds.length-1?'end':'middle')+'">'+ds[i]+'</text>').join('');
  const marks=ds.filter(d=>eventMap.has(d)).map(d=>'<g data-event-date="'+d+'"><line x1="'+x(d)+'" x2="'+x(d)+'" y1="'+T+'" y2="'+pe+'" stroke="#bc83e7" stroke-opacity=".45" stroke-dasharray="3 4"/><circle cx="'+x(d)+'" cy="'+(T+5)+'" r="4" fill="#bc83e7"><title>'+E(d+' · '+eventMap.get(d).length+' source-linked event(s)')+'</title></circle></g>').join('');
  plot.innerHTML='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+E(label||'Native chart')+'"><defs><clipPath id="sw49clip'+(host.id||'chart')+'"><rect x="'+L+'" y="'+T+'" width="'+(Xend-L)+'" height="'+(pe-T)+'"/></clipPath></defs>'+grid+'<g clip-path="url(#sw49clip'+(host.id||'chart')+')">'+price+(sma?path(ind.sma,'#8caef8'):'')+(ema?path(ind.ema,'#ecc37a'):'')+lines+'</g>'+volume+ticks+marks+'<line data-crosshair class="sw49-cross" y1="'+T+'" y2="'+(H-B)+'"/><line data-horizontal class="sw49-cross" x1="'+L+'" x2="'+Xend+'"/></svg>';
  lower.hidden=!rsi;
  lower.innerHTML=rsi?'<svg viewBox="0 0 '+W+' 100" role="img" aria-label="RSI 14 observations"><rect x="'+L+'" y="24" width="'+(Xend-L)+'" height="32" fill="var(--sw-card-hi)"/><path d="M'+L+' 24H'+Xend+'M'+L+' 56H'+Xend+'" class="sw49-cross"/><polyline fill="none" stroke="#bc83e7" stroke-width="1.7" points="'+ind.rsi.filter(p=>dset.has(p.date)).map(p=>x(p.date)+','+(80-p.value*.8)).join(' ')+'"/><text x="'+(Xend+7)+'" y="28">70</text><text x="'+(Xend+7)+'" y="60">30</text><text x="'+L+'" y="94">RSI 14</text><line data-crosshair class="sw49-cross" y1="0" y2="80"/></svg>':'';
  slider.max=String(ds.length-1);slider.value=String(cursor-range.start);
  host.querySelector('[data-window]').textContent=ds.length+' / '+dates.length+' dates · '+ds[0]+' – '+ds.at(-1);
  host.querySelector('[data-tool]').textContent=tool==='trend'?(first?'Choose second point':'Choose first trendline point'):tool==='horizontal'?'Click a price level':'Drag to pan · wheel to zoom';
  for(const [k,on] of Object.entries({line:mode==='line',candles:mode==='candles',sma,ema,rsi,volume:showVolume,pan:tool==='pan',trend:tool==='trend',horizontal:tool==='horizontal'}))active(k,on);
  inspect(cursor);
 }
 function inspect(i,yPos){
  cursor=Math.max(range.start,Math.min(range.end-1,i));const d=dates[cursor],x=geom.x(d);
  host.querySelectorAll('[data-crosshair]').forEach(l=>{l.setAttribute('x1',x);l.setAttribute('x2',x)});
  const line=plot.querySelector('[data-horizontal]');const v=Number.isFinite(yPos)?Math.min(geom.pe,Math.max(T,yPos)):geom.y(sets[0].points.find(p=>p.date===d)?.value??geom.lo);
  line.setAttribute('y1',v);line.setAttribute('y2',v);
  slider.value=String(cursor-range.start);
  const row=map.get(d),r=ind.rsi.find(p=>p.date===d);
  info.textContent=d+' · '+(row?(candles?'O '+F(row.open)+' H '+F(row.high)+' L '+F(row.low)+' ':'')+'Close '+F(row.close)+' '+unit+(num(row.volume)?' · Vol '+F(row.volume):''):sets.map(s=>s.label+' '+F(s.points.find(p=>p.date===d)?.raw??s.points.find(p=>p.date===d)?.value)+' '+(s.unit||unit)).join(' · '))+(rsi&&r?' · RSI '+F(r.value):'');const eventPanel=host.querySelector('[data-chart-events]');eventPanel.replaceChildren();for(const e of (eventMap.get(d)||[]).slice(0,8)){const line=document.createElement('div'),a=document.createElement('a');a.href=e.url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=e.headline;line.append(document.createTextNode('Published UTC · '+(e.confidence==='strong'?'Issuer-confirmed':'Named reference')+' · '),a);eventPanel.append(line)}if((eventMap.get(d)||[]).length>8)eventPanel.append(document.createTextNode('More events in company event lens.'));if(!silent&&onChange)onChange({start:range.start,end:range.end,cursor,date:d,firstDate:dates[range.start],lastDate:dates[range.end-1]});
 }
 const indexAt=e=>{const q=plot.getBoundingClientRect(),px=(e.clientX-q.left)/q.width*W;return Math.max(range.start,Math.min(range.end-1,range.start+Math.round((px-L)/(Xend-L)*(range.end-range.start-1))))};
 const yAt=e=>(e.clientY-plot.getBoundingClientRect().top)/plot.getBoundingClientRect().height*H;
 function action(k){if(['older','newer','in','out','reset'].includes(k)){range=A.navigateChart(dates.length,range,k,cursor);if(k==='reset'&&onReset)onReset()}else if(k==='line'||k==='candles')mode=k;else if(k==='sma')sma=!sma;else if(k==='ema')ema=!ema;else if(k==='rsi')rsi=!rsi;else if(k==='volume')showVolume=!showVolume;else if(k==='clear'){drawings=[];first=null}else if(['pan','trend','horizontal'].includes(k)){tool=k;first=null}paint()}
 host.querySelectorAll('[data-act]').forEach(btn=>btn.addEventListener('click',()=>action(btn.dataset.act)));
 slider.oninput=()=>inspect(range.start+Number(slider.value));
 plot.addEventListener('wheel',e=>{if(!e.ctrlKey&&!e.shiftKey&&document.activeElement!==plot)return;e.preventDefault();cursor=indexAt(e);action(e.deltaY<0?'in':'out')},{passive:false});
 plot.addEventListener('pointerdown',e=>{if(e.button!==0)return;if(e.pointerType==='touch'&&tool==='pan'){pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});plot.setPointerCapture(e.pointerId);if(pointers.size===2){const [a,b]=[...pointers.values()];pinch={distance:Math.max(1,Math.hypot(a.x-b.x,a.y-b.y)),count:range.end-range.start,anchor:indexAt({clientX:(a.x+b.x)/2})};drag=null;return}}plot.focus({preventScroll:true});if(tool==='pan'){drag={x:e.clientX,start:range.start,count:range.end-range.start,id:e.pointerId};plot.setPointerCapture(e.pointerId)}else{const pos={date:dates[indexAt(e)],value:geom.hi-(Math.min(geom.pe,Math.max(T,yAt(e)))-T)/(geom.pe-T)*(geom.hi-geom.lo)};if(tool==='horizontal')drawings.push({kind:tool,a:pos});else if(first){drawings.push({kind:tool,a:first,b:pos});first=null}else first=pos;paint()}});
 plot.addEventListener('pointermove',e=>{if(pointers.has(e.pointerId)){pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});if(pinch&&pointers.size===2){const [a,b]=[...pointers.values()];const size=Math.round(pinch.count*pinch.distance/Math.max(1,Math.hypot(a.x-b.x,a.y-b.y)));range=A.chartWindow(dates.length,pinch.anchor-size/2,size);paint();return}}if(drag&&drag.id===e.pointerId){const count=drag.count,shift=Math.round((drag.x-e.clientX)/Math.max(1,plot.clientWidth)*count);range=A.chartWindow(dates.length,drag.start+shift,count);paint()}else inspect(indexAt(e),yAt(e))});
 for(const k of ['pointerup','pointercancel','lostpointercapture'])plot.addEventListener(k,e=>{pointers.delete(e.pointerId);pinch=null;if(drag?.id===e.pointerId)drag=null});
 plot.addEventListener('keydown',e=>{if(e.key==='ArrowLeft'||e.key==='ArrowRight'){e.preventDefault();inspect(cursor+(e.key==='ArrowLeft'?-1:1))}else if(e.key==='+'||e.key==='-'){e.preventDefault();action(e.key==='+'?'in':'out')}});
 paint();return {window:()=>({...range}),candles,hasVolume,dates:[...dates],inspectDate(d){const i=dates.indexOf(d);if(i<0)return false;cursor=i;if(i<range.start||i>=range.end){range=A.chartWindow(dates.length,i-Math.floor((range.end-range.start)/2),range.end-range.start);paint()}else inspect(i);return true},sync(v){if(!v||dates[v.cursor]!==v.date||dates[v.start]!==v.firstDate||dates[v.end-1]!==v.lastDate)return false;silent=true;try{const next=A.chartWindow(dates.length,v.start,v.end-v.start);cursor=v.cursor;if(next.start!==range.start||next.end!==range.end){range=next;paint()}else inspect(cursor);return true}finally{silent=false}}};
}
const api={cleanBars,authorized,mount};if(typeof module==='object'&&module.exports)module.exports=api;else global.StockwatchNativeChart=api;
})(typeof window!=='undefined'?window:{});
