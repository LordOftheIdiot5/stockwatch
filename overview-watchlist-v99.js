/* V99: saved research tickers on this device; no simulated portfolio. */
(function(global){
'use strict';
const KEYS=['stockwatch-terminal-v31','stockwatch-v4-favorites'];
function read(key){
 try{
   const value=JSON.parse(global.localStorage.getItem(key)||'null');
   const items=key===KEYS[0]?value?.pinned:value;
   return Array.isArray(items)?items.filter(x=>typeof x==='string'&&x.length>0&&x.length<=80).slice(0,100):[];
 }catch{return []}
}
function saved(){return [...new Set(KEYS.flatMap(read))].slice(0,100)}
function observed(r){
 return !!(r&&!r.referenceOnly&&!r.unavailable&&typeof r.close==='number'&&Number.isFinite(r.close)&&r.close>0&&typeof r.currency==='string'&&r.currency&&typeof r.date==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(r.date)&&!Number.isNaN(Date.parse(r.date)));
}
function make(tag,cls,value){
 const el=document.createElement(tag);
 if(cls)el.className=cls;
 if(value!==undefined)el.textContent=String(value);
 return el;
}
function mount({parent,rows}={}){
 if(!parent||!Array.isArray(rows)||parent.querySelector('#overviewWatchlist'))return;
 const host=make('section','sw-panel sw99-watchlist');
 host.id='overviewWatchlist';
 host.setAttribute('aria-labelledby','overviewWatchTitle');
 host.setAttribute('aria-live','polite');
 parent.classList.add('sw99-watch-pair');parent.append(host);
 const known=new Map();
 for(const r of rows){
   if(!r||typeof r.ticker!=='string'||!r.ticker)continue;
   const old=known.get(r.ticker);
   if(!old||(old.referenceOnly&&!r.referenceOnly))known.set(r.ticker,r);
 }
 function paint(){
   const selected=saved(),entries=selected.map(k=>known.get(k)).filter(Boolean).slice(0,12);
   host.replaceChildren();
   const head=make('header','sw-panel-hd');
   const title=make('h2','','My watchlist');title.id='overviewWatchTitle';
   head.append(title,make('small','',entries.length+' saved listing'+(entries.length===1?'':'s')+' shown · this browser'));
   host.append(head);
   if(!selected.length){
      const empty=make('div','sw99-watch-empty');
      empty.append(make('p','','No saved companies yet. Star a listing in Stocks & sectors, or save it from the Research terminal.'));
      const a=make('a','sw-textlink','Browse companies ↗');a.href='stocks.html';empty.append(a);
      host.append(empty);return;
   }
   if(!entries.length){
      host.append(make('div','sw99-watch-empty','Saved tickers are not in the current research directory. No price was inferred.'));return;
   }
   const list=make('div','sw99-watch-rows');
   for(const r of entries){
      const a=make('a','sw99-watch-row');
      a.dataset.watchlistRow=r.ticker;
      a.href=r.registryOnly?'directory.html?q='+encodeURIComponent(r.figi||r.ticker):
             r.referenceOnly?'company.html?ticker='+encodeURIComponent('ref:'+(r.referenceId||r.ticker)):
             'company.html?ticker='+encodeURIComponent(r.ticker);
      const identity=make('span','sw99-watch-identity');
      identity.append(make('strong','',r.name||r.symbol||r.ticker),
                      make('small','',r.ticker+' · '+(r.exchange||'Research listing')));
      const quote=make('span','sw99-watch-quote');
      if(observed(r)){
        const price=r.close.toLocaleString('en-GB',{maximumFractionDigits:4});
        quote.append(make('strong','',price+' '+r.currency),
                     make('small','',(r.priceStatus==='retained'?'Last saved':'Reported')+' · '+r.date));
      }else{
        quote.append(make('strong','',r.referenceOnly?'Reference only':'Price unavailable'),
                     make('small','','No authorized price observation connected'));
      }
      a.append(identity,quote);list.append(a);
   }
   host.append(list);
   host.append(make('p','sw-meta sw99-watch-note','Saved tickers are stored in this browser. These are dated observations, not live quotes or a simulated portfolio. No quantity or market value is assumed.'));
   const links=make('div','sw99-watch-actions');
   const stocks=make('a','sw-textlink','Edit in Stocks & sectors ↗');stocks.href='stocks.html';
   const terminal=make('a','sw-textlink','Research terminal ↗');terminal.href='terminal.html';
   links.append(stocks,terminal);host.append(links);
 }
 paint();
 global.addEventListener('storage',event=>{if(!event.key||KEYS.includes(event.key))paint()});
}
const api={mount,read,saved,observed};
if(typeof module==='object'&&module.exports)module.exports=api;
else global.StockwatchOverviewWatchlist=api;
})(typeof window!=='undefined'?window:globalThis);
