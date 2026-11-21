/* V93 Heatmap Experience — presentation derived ONLY from existing rendered tiles.
 * No price fetch, hidden exchange data, invented market caps or navigation changes.
 * Supports dynamic Overview and Stocks/Screener tiles as filters refresh.
 */
(function(factory){
  "use strict";
  const api=factory();
  if(typeof module!=="undefined" && module.exports){module.exports=api;return;}
  if(typeof document==="undefined")return;

  const ROOTS=["workspaceHeatmap","stkHeat"];
  const mounted=new WeakSet();
  const sourceRecord=new WeakMap();
  const lastTileSignatures=new WeakMap();

  function node(tag,text,cls){
    const item=document.createElement(tag);
    item.textContent=String(text);
    if(cls)item.className=cls;
    return item;
  }
  function safeLink(href,base){
    try{
      const url=new URL(href,base);
      return url.origin===new URL(base).origin &&
        /^\/(?:company|directory)\.html$/.test(url.pathname) ? url.href : null;
    }catch(_){return null;}
  }
  function display(root,tile){
    const dock=sourceRecord.get(root);
    if(!dock)return;
    const panel=dock.querySelector(".sw93-heat-detail");
    if(!panel)return;
    panel.replaceChildren();
    const picker=dock.querySelector(".sw93-heat-picker");
    if(!tile || !root.contains(tile)){
      if(picker)picker.value="";
      panel.append(node("p","Focus or hover over a company tile to inspect its dated observation.","sw93-heat-hint"));
      return;
    }
    // Pointer and keyboard focus can override the selector's preview. Keep
    // the selected option identical to the company displayed in the card.
    if(picker){
      const tileIndex=[...root.querySelectorAll("a.sw-heat-cell")].indexOf(tile);
      if(tileIndex>=0 && picker.value!==String(tileIndex))picker.value=String(tileIndex);
    }
    const info=api.describe({
      title:tile.getAttribute("title"),
      label:tile.getAttribute("aria-label"),
      ticker:tile.querySelector("strong")?.textContent,
      change:tile.querySelector("span")?.textContent,
      classes:tile.className
    });
    const top=node("div","","sw93-heat-detail-head");
    top.append(node("span",info.ticker || "Company", "sw93-heat-ticker"));
    top.append(node("strong",info.change||info.status,"sw93-heat-change "+info.css));
    panel.append(top);
    panel.append(node("p",info.details,"sw93-heat-full"));
    panel.append(node("small",info.note,"sw93-heat-note"));
    const url=safeLink(tile.getAttribute("href"),location.href);
    if(url){
      const link=document.createElement("a");
      link.href=url;
      link.textContent="Open company research";
      link.className="sw93-heat-link";
      panel.append(link);
    }
  }
  function refresh(root){
    const dock=sourceRecord.get(root);
    if(!dock)return;
    // The screener initially shows a table. Never expose an orphan inspector
    // while its associated heatmap container is hidden.
    dock.hidden=Boolean(root.hidden);
    dock.style.display=root.hidden?"none":"";
    const tiles=[...root.querySelectorAll("a.sw-heat-cell")];
    const summary=api.countStates(tiles.map(el=>el.className));
    const key=[summary.up,summary.down,summary.flat,summary.unavailable].join("|");
    const picker=dock.querySelector(".sw93-heat-picker");
    const signature=tiles.map(el=>el.getAttribute("href")+"|"+el.getAttribute("title")).join("||");
    if(lastTileSignatures.get(root)!==signature){
      lastTileSignatures.set(root,signature);
      picker.replaceChildren();
      const blank=node("option","Choose a tile…");
      blank.value="";
      picker.append(blank);
      tiles.forEach((tile,i)=>{
        const label=tile.querySelector("strong")?.textContent||"Company";
        const change=tile.classList.contains("no-data")?"No movement data":tile.querySelector("span")?.textContent||"Movement unavailable";
        const option=node("option",label+" · "+change);
        option.value=String(i);
        picker.append(option);
      });
    }
    if(dock.dataset.countKey===key)return;
    dock.dataset.countKey=key;
    const counts=dock.querySelector(".sw93-heat-counts");
    counts.replaceChildren();
    for(const [name,label] of [
      ["up","Gain"],["down","Loss"],["flat","Flat"],["unavailable","No movement data"]
    ]){
      const cell=node("span",label+": "+summary[name],"sw93-heat-count sw93-"+name);
      counts.append(cell);
    }
    const track=dock.querySelector(".sw93-heat-balance");
    track.replaceChildren();
    for(const [name,label] of [
      ["up","Gain"],["flat","Flat"],["down","Loss"],["unavailable","No movement data"]
    ]){
      const seg=node("span","","sw93-heat-segment sw93-"+name);
      seg.style.width=summary.total ? (100*summary[name]/summary.total).toFixed(2)+"%" : "0%";
      seg.title=label+": "+summary[name]+" visible tiles";
      track.append(seg);
    }
    track.setAttribute("aria-label",
      summary.total+" visible tiles: "+summary.up+" gains, "+summary.down+
      " losses, "+summary.flat+" flat, "+summary.unavailable+" without movement data");
    dock.querySelector(".sw93-heat-total").textContent=summary.total+" visible tiles";
  }
  function mount(root){
    if(mounted.has(root))return;
    mounted.add(root);
    const dock=node("section","","sw93-heat-inspector");
    dock.setAttribute("aria-label","Heatmap observation inspector");
    const heading=node("div","","sw93-heat-inspector-head");
    const headingCopy=node("div","","sw93-heat-heading");
    headingCopy.append(node("strong","Inspect the map"));
    headingCopy.append(node("small","Visible tiles only · not whole-market breadth"));
    heading.append(headingCopy);
    const controls=node("div","","sw93-heat-actions");
    const total=node("span","0 visible tiles","sw93-heat-total");
    controls.append(total);
    const large=node("button","Larger tiles","sw93-heat-size");
    large.type="button";
    large.setAttribute("aria-pressed","false");
    large.addEventListener("click",()=>{
      const enabled=root.classList.toggle("sw93-heat-comfortable");
      large.setAttribute("aria-pressed",String(enabled));
      large.textContent=enabled?"Compact tiles":"Larger tiles";
    });
    controls.append(large);
    heading.append(controls);
    dock.append(heading);
    const summary=node("div","","sw93-heat-counts");
    dock.append(summary);
    const bar=node("div","","sw93-heat-balance");
    bar.setAttribute("role","img");
    dock.append(bar);
    const pickerRow=node("div","","sw93-heat-picker-row");
    const pickerLabel=node("label","Inspect a company tile","sw93-heat-picker-label");
    const picker=document.createElement("select");
    picker.id=root.id+"-inspector-picker";
    picker.className="sw93-heat-picker";
    pickerLabel.htmlFor=picker.id;
    picker.addEventListener("change",()=>{
      const index=Number(picker.value);
      const tiles=[...root.querySelectorAll("a.sw-heat-cell")];
      display(root,picker.value!==""&&Number.isInteger(index)?tiles[index]:null);
    });
    pickerRow.append(pickerLabel,picker);
    dock.append(pickerRow);
    const detail=node("div","","sw93-heat-detail");
    detail.setAttribute("aria-live","polite");
    detail.setAttribute("aria-atomic","true");
    dock.append(detail);
    // Adjacent to the existing heatmap; do not move existing controls or tiles.
    root.insertAdjacentElement("afterend",dock);
    sourceRecord.set(root,dock);
    root.addEventListener("focusin",event=>{
      const tile=event.target.closest?.("a.sw-heat-cell");
      if(tile)display(root,tile);
    });
    root.addEventListener("pointerover",event=>{
      if(event.pointerType==="touch")return;
      const tile=event.target.closest?.("a.sw-heat-cell");
      if(tile)display(root,tile);
    });
    const observer=new MutationObserver(()=>{
      refresh(root);
      const current=root.querySelector("a.sw-heat-cell:focus");
      if(current)display(root,current);
      else if(!root.contains(document.activeElement)&&!dock.querySelector(".sw93-heat-picker")?.value)display(root,null);
    });
    observer.observe(root,{subtree:true,childList:true});
    refresh(root);
    display(root,null);
  }
  function init(){
    const app=document.querySelector("#v4app");
    if(!app)return;
    const ensure=()=>{
      for(const id of ROOTS){
        const root=document.getElementById(id);
        if(root && app.contains(root))mount(root);
      }
    };
    ensure();
    const live=new MutationObserver(ensure);
    // Some views build their tile container asynchronously or on a filter click.
    live.observe(app,{subtree:true,childList:true});
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});
  else init();
})(function(){
  "use strict";
  function countStates(classes){
    const result={up:0,down:0,flat:0,unavailable:0,total:0};
    for(const entry of Array.isArray(classes)?classes:[]){
      if(typeof entry!=="string")continue;
      const names=new Set(entry.split(/\s+/));
      if(!names.has("sw-heat-cell"))continue;
      result.total++;
      if(names.has("no-data"))result.unavailable++;
      else if(names.has("positive"))result.up++;
      else if(names.has("negative"))result.down++;
      else result.flat++;
    }
    return result;
  }
  function describe({title,label,ticker,change,classes}={}){
    const raw=typeof title==="string" ? title.trim().slice(0,550) : "";
    const fallback=typeof label==="string"?label.trim().slice(0,550):"";
    const t=typeof ticker==="string"?ticker.trim().slice(0,45):"";
    const c=typeof change==="string"?change.trim().slice(0,45):"";
    const tags=new Set(String(classes||"").split(/\s+/));
    const status=tags.has("no-data")?"No verified movement":
      tags.has("positive")?"Gain":tags.has("negative")?"Loss":"Flat movement";
    const css=tags.has("no-data")?"sw93-unavailable":
      tags.has("positive")?"sw93-up":tags.has("negative")?"sw93-down":"sw93-flat";
    const dated=(raw||fallback).match(/\b20\d{2}-\d{2}-\d{2}\b/)?.[0]||"";
    const retained=/last saved|saved observation|saved movement|refresh unavailable|older|retained/i.test(raw);
    const note=retained ? "Dated retained/older data — not a live price." :
      dated ? "Reported date "+dated+" · verify source and trading session on the company page." :
      "No confirmed observation date in the tile; verify the company source.";
    return {ticker:t,change:tags.has("no-data")?"":c,status,css,details:raw||fallback||"No details supplied for this tile.",
      date:dated,note,retained};
  }
  return {countStates,describe};
});
