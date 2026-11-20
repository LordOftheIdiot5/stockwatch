(()=>{'use strict';
 const host=document.getElementById('globalIndexData');if(!host)return;
 const source='https://data.gov.tw/en/datasets/11672',license='https://data.gov.tw/en/license';
 function el(tag,text,cls){const n=document.createElement(tag);n.textContent=text;if(cls)n.className=cls;return n}
 function link(text,url){const a=el('a',text,'sw-textlink');a.href=url;return a}
 function chart(history,latest){
  const rows=(Array.isArray(history)?history:[]).filter(x=>x&&Number.isFinite(x.close)&&x.close>0&&typeof x.date==='string'&&x.date<=latest.date).sort((a,b)=>a.date.localeCompare(b.date)).slice(-20);
  if(rows.length<2)return null;
  const values=rows.map(x=>x.close),min=Math.min(...values),max=Math.max(...values),range=max-min||1;
  const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg'),path=document.createElementNS(ns,'polyline');
  svg.setAttribute('viewBox','0 0 120 42');svg.setAttribute('role','img');svg.setAttribute('aria-label','Recent official TAIEX closes, '+rows[0].date+' to '+rows[rows.length-1].date);
  path.setAttribute('points',values.map((v,i)=>(2+i*116/(values.length-1)).toFixed(2)+','+(39-(v-min)*36/range).toFixed(2)).join(' '));path.setAttribute('fill','none');path.setAttribute('stroke','currentColor');path.setAttribute('stroke-width','1.8');path.setAttribute('stroke-linejoin','round');svg.append(path);return svg;
 }
 fetch('data/global-indices-v1.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('unavailable');return r.json()}).then(d=>{
  const x=d.latest;if(d.key!=='twse:TAIEX'||!x||!Number.isFinite(x.close)||!Number.isFinite(x.changePct)||!/^\d{4}-\d{2}-\d{2}$/.test(x.date))throw Error('invalid');
  const card=el('article','','sw-index-card'),main=el('div','','sw-index-main'),top=el('div','','sw-index-top'),change=el('strong',(x.changePct>0?'+':'')+x.changePct.toFixed(2)+'%',x.changePct>0?'sw-up':x.changePct<0?'sw-down':'');
  top.append(el('span','Taiwan · TAIEX'),change);
  main.append(top,el('b',x.close.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}),'sw-index-close'),el('small',x.date+(d.status==='ok'?' · Closed':' · Retained; refresh failed')));
  const spark=chart(d.history,x);if(spark){const graph=el('div','','sw-index-spark');graph.classList.add(x.changePct>0?'sw-up':x.changePct<0?'sw-down':'sw-meta');graph.append(spark);main.append(graph)}
  const foot=el('div','','sw-index-foot');foot.append(link('TWSE source',source),link('Open licence',license));card.append(main,foot);host.replaceChildren(card);
 }).catch(()=>{const card=el('div','','sw-index-card');card.append(el('strong','Taiwan · TAIEX'),el('p','Last closing data unavailable.','sw-meta'),link('Official source',source));host.replaceChildren(card)});
})();