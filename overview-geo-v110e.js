/* V110e — real listing coverage, located geographically. No market-return pins. */
(function () {
  'use strict';
  if (document.body.dataset.page !== 'index') return;
  const host = document.getElementById('v4app');
  if (!host) return;

  // Only exchange cities with unambiguous identities are plotted. Others
  // remain in the complete text list. Pins represent listing coverage only.
  const EUROPE = new Set([
    'Stockholm','Helsinki','Copenhagen','Oslo','London','XETRA',
    'Paris','Amsterdam','SIX Swiss','Brussels','Irish','Milan','Vienna'
  ]);
  const ASIA = new Set(['HKSE']);
  function make(tag, className, value) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (value != null) el.textContent = String(value);
    return el;
  }
  function mapGroup(byVenue, known) {
    const rows = byVenue.filter(v=>known.has(v?.venue) && Number.isInteger(v.listings)
      && v.listings>0 && Number.isInteger(v.datedPrice)
      && v.datedPrice>=0 && v.datedPrice<=v.listings);
    return {listed:rows.reduce((sum,v)=>sum+v.listings,0),
      dated:rows.reduce((sum,v)=>sum+v.datedPrice,0),count:rows.length};
  }
  function position(lon,lat) {
    return {x:Math.min(100,Math.max(0,(lon+180)/360*100)),
      y:Math.min(100,Math.max(0,(85-lat)/155*100))};
  }
  function addPin(area,label,stats,lon,lat) {
    if (!stats.listed) return;
    const pos=position(lon,lat);
    const pin=make('button','sw110e-pin');
    pin.type='button';
    pin.style.left=pos.x.toFixed(2)+'%';
    pin.style.top=pos.y.toFixed(2)+'%';
    pin.setAttribute('aria-label',label+': '+stats.dated+' of '+stats.listed+' listings with dated prices. This is not a market movement.');
    pin.setAttribute('title',label+': '+stats.dated+'/'+stats.listed+' dated observations, not market returns');
    const dot=make('span','sw110e-pin-dot');
    dot.setAttribute('aria-hidden','true');
    const text=make('span','sw110e-pin-tooltip',label+' · '+stats.dated+'/'+stats.listed);
    text.setAttribute('aria-hidden','true');
    pin.append(dot,text);
    pin.addEventListener('click',()=>{pin.classList.toggle('sw110e-pin-open')});
    area.append(pin);
  }
  function renderCoverageMap(section,data) {
    const body=section.querySelector('.sw110d-coverage-body');
    const rows=body?.querySelector('.sw110d-venue-list');
    if (!body || !rows || section.querySelector('.sw110e-world')) return false;
    const all=data?.byVenue;
    if (!Array.isArray(all) || data?.schemaVersion!==1) return false;
    const europe=mapGroup(all,EUROPE);
    const asia=mapGroup(all,ASIA);
    const unmapped=all.filter(v=>!EUROPE.has(v.venue)&&!ASIA.has(v.venue));
    const label=make('p','sw110e-map-heading','Mapped research coverage');
    const world=make('div','sw110e-world');
    world.setAttribute('role','group');
    world.setAttribute('aria-label','Geographic listing coverage. Europe and Hong Kong are shown where source venue identity is unambiguous; no financial returns are inferred.');
    const geography=make('img','sw110e-map-land');
    geography.src='brand/world-land-ne110.svg';
    geography.alt='';
    geography.setAttribute('aria-hidden','true');
    geography.loading='lazy';
    world.append(geography);
    addPin(world,'Europe',europe,11,53);
    addPin(world,'Hong Kong',asia,114.17,22.32);
    const legend=make('div','sw110e-map-legend');
    legend.append(make('span','','● Exchange listing coverage'));
    legend.append(make('span','','Not index performance'));
    const details=make('details','sw110e-all-venues');
    const summary=make('summary','', 'All exchange venues ('+all.length+')');
    details.append(summary,rows);
    const caption=body.querySelector('.sw110d-coverage-caption');
    if(caption)caption.after(label,world,legend,details);
    else body.append(label,world,legend,details);
    if(unmapped.length) {
      details.append(make('p','sw-meta','Unmapped venue identifiers remain in the list; none are placed on the map without identity review.'));
    }
    return true;
  }
  async function mount(section) {
    if (section.dataset.sw110e || !section.querySelector('.sw110d-venue-list')) return false;
    section.dataset.sw110e='loading';
    try {
      const res=await fetch('data/daily-price-coverage-v105.json',{cache:'no-store'});
      if(!res.ok)throw new Error('coverage unavailable');
      const data=await res.json();
      if (section.isConnected && renderCoverageMap(section,data)) section.dataset.sw110e='ready';
      else section.dataset.sw110e='unavailable';
    } catch {
      section.dataset.sw110e='unavailable';
    }
    return true;
  }
  const attempt=()=>{
    const section=host.querySelector('.sw110d-market-coverage');
    if(section?.querySelector('.sw110d-venue-list')) {mount(section);return true}
    return false;
  };
  if(attempt())return;
  const observer=new MutationObserver(()=>{if(attempt())observer.disconnect()});
  observer.observe(host,{subtree:true,childList:true});
  window.addEventListener('pagehide',()=>observer.disconnect(),{once:true});
})();