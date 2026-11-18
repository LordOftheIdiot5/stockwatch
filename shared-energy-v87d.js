(()=>{"use strict";
const host=document.getElementById("sharedEnergyContext");if(!host)return;
const node=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n};
const number=(n,d=0)=>n.toLocaleString("en-GB",{maximumFractionDigits:d});
fetch("data/shared-energy-context.json",{cache:"no-cache"}).then(r=>{if(!r.ok)throw Error();return r.json()}).then(d=>{
 if(d.schemaVersion!==1||!Array.isArray(d.zones)||d.zones.length!==5||d.zones.some((z,i)=>z.zone!=="NO"+(i+1)||!Number.isFinite(z.capacityMW)||z.capacityMW<0||!Number.isInteger(z.plants)||!Number.isInteger(z.capacityRecords)))throw Error();
 const status=document.getElementById("sharedEnergyStatus");
 status.textContent=number(d.plants)+" plant records · "+number(d.missingCapacity)+" lack a capacity value · source dated "+String(d.sourceGenerated).slice(0,10)+(d.refreshStatus==="retained"?" · previous snapshot retained":"");
 const wrap=node("div",undefined,"sw-intel-mini");
 const maximum=Math.max(...d.zones.map(z=>z.capacityMW),1);
 for(const z of d.zones){const card=node("div",undefined,"sw-peer");card.append(node("small",z.zone),node("strong",number(z.capacityMW,1)+" MW"),node("span",number(z.plants)+" plant records · "+number(z.capacityRecords)+" with capacity"));const bar=node("meter");bar.min=0;bar.max=maximum;bar.value=z.capacityMW;bar.setAttribute("aria-label",z.zone+" reported capacity");bar.style.width="100%";card.append(bar);wrap.append(card)}
 document.getElementById("sharedEnergyRows").replaceChildren(wrap);
}).catch(()=>{document.getElementById("sharedEnergyStatus").textContent="Shared energy snapshot unavailable. Visit Energy Nordl for original data."});
})();
