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
 const feeds=[
 {key:'twse:TAIEX',path:'data/global-indices-v1.json',label:'Taiwan · TAIEX',source:'https://data.gov.tw/en/datasets/11672',credit:'TWSE source'},
 {key:'tpex:TPEx',path:'data/global-index-tpex.json',label:'Taipei Exchange · TPEx',source:'https://data.gov.tw/dataset/11391',credit:'TPEx source'},
 {key:'twse:FORMOSA',path:'data/global-index-formosa.json',label:'Taiwan · Formosa',source:'https://data.gov.tw/dataset/11669',credit:'TWSE cross-market source'}
 ];
 function draw(d,cfg){
  const x=d.latest;if(d.key!==cfg.key||!x||!Number.isFinite(x.close)||x.close<=0||!/^\d{4}-\d{2}-\d{2}$/.test(x.date))throw Error('invalid');
  const pc=Number.isFinite(x.changePct),sign=pc?(x.changePct>0?'sw-up':x.changePct<0?'sw-down':''):'';
  const card=el('article','','sw-index-card'),main=el('div','','sw-index-main'),top=el('div','','sw-index-top'),change=el('strong',pc?(x.changePct>0?'+':'')+x.changePct.toFixed(2)+'%':'—',sign);
  top.append(el('span',cfg.label),change);
  main.append(top,el('b',x.close.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}),'sw-index-close'),el('small',x.date+(d.status==='ok'?' · Closed':' · Retained; refresh failed')));
  if(!pc)main.append(el('small','Comparable prior close unavailable'));
  const spark=chart(d.history,x);if(spark){spark.setAttribute('aria-label',cfg.label+' historical closes through '+x.date);const graph=el('div','','sw-index-spark');graph.classList.add(sign||'sw-meta');graph.append(spark);main.append(graph)}
  const foot=el('div','','sw-index-foot');foot.append(link(cfg.credit,cfg.source),link('Open licence',license));card.append(main,foot);return card;
 }
 Promise.all(feeds.map(cfg=>fetch(cfg.path,{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error('unavailable');return r.json()}).then(d=>draw(d,cfg)).catch(()=>{if(cfg.key!=='twse:TAIEX')return null;const card=el('div','','sw-index-card');card.append(el('strong',cfg.label),el('p','Last closing data unavailable.','sw-meta'),link('Official source',cfg.source));return card}))).then(cards=>host.replaceChildren(...cards.filter(Boolean)));
})();