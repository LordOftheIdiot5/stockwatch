/* V100 Nasdaq Nordic source-dated RSS notice list.
 * No issuer match, price quote or copied article/attachment. */
(function(){
'use strict';
const host=document.getElementById('nasdaqNoticeItems');
const state=document.getElementById('nasdaqNoticeStatus');
const count=document.getElementById('nasdaqNoticeCount');
if(!host||!state||!count)return;
function validLink(value){
 try{
   const u=new URL(value);
   return u.protocol==='https:'&&
     ['view.news.eu.nasdaq.com','api.news.eu.nasdaq.com','www.nasdaq.com'].includes(u.hostname)&&
     !u.username&&!u.password?u.href:null;
 }catch{return null}
}
function el(tag,cls,content){
 const item=document.createElement(tag);
 if(cls)item.className=cls;
 if(content!==undefined)item.textContent=content;
 return item;
}
fetch('data/nasdaq-nordic-notices.json?v='+Date.now(),{cache:'no-store'})
 .then(r=>{if(!r.ok)throw Error('not_collected');return r.json()})
 .then(d=>{
   const sources=Object.values(d.sources||{});
   const ok=sources.length===2&&sources.every(s=>s.status==='ok');
   const rows=(Array.isArray(d.items)?d.items:[])
     .filter(x=>x&&typeof x.title==='string'&&x.title.length<=280&&
       validLink(x.url)&&Number.isFinite(Date.parse(x.published)))
     .sort((a,b)=>Date.parse(b.published)-Date.parse(a.published)).slice(0,12);
   count.textContent=(Array.isArray(d.items)?d.items.length:0)+' original notices';
   state.textContent=ok?'Source RSS checks succeeded; dates belong to original notices':
     'RSS refresh incomplete or unavailable; earlier source-dated notices may be retained';
   host.replaceChildren();
   for(const x of rows){
     const box=el('article','sw100-notice');
     const a=el('a','sw-textlink',x.title+' ↗');
     a.href=validLink(x.url);a.target='_blank';a.rel='noopener noreferrer';
     const small=el('small','',String(x.category||'Nasdaq Nordic')+' · '+
       String(x.published).slice(0,16).replace('T',' ')+' UTC');
     box.append(a,small);host.append(box);
   }
   if(!rows.length)host.append(el('p','sw-meta',
     'No original Nasdaq notices are available in the saved source snapshot.'));
 })
 .catch(()=>{
   state.textContent='Official Nordic RSS notices have not been collected yet';
   host.replaceChildren(el('p','sw-meta',
     'Original notices temporarily unavailable; no headlines were invented.'));
 });
})();
