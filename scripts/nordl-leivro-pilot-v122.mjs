// Private candidate for catalog observations, not certification dates or SKU availability.
import {observation} from './nordl-observation-v122.mjs';
const url='https://data.energystar.gov/d/wati-2tfp';
export function leivroPilot(snapshot,asOf){
 const missing=reason=>({schemaVersion:1,asOf,results:[],missing:[reason],publicEligible:false});
 try{
 if(snapshot.schema_version!==1||snapshot.status!=='ok'||snapshot.source!==url||snapshot.dataset_id!=='wati-2tfp'||snapshot.full_snapshot!==true) return missing('incomplete_or_unrecognized_catalog');
 if(!Array.isArray(snapshot.products)||!Number.isInteger(snapshot.source_rows)||snapshot.source_rows<1||snapshot.source_rows>8000||snapshot.normalized_rows!==snapshot.products.length||!Number.isInteger(snapshot.rejected_rows)||snapshot.rejected_rows<0||snapshot.normalized_rows+snapshot.rejected_rows!==snapshot.source_rows||snapshot.normalized_rows<Math.max(5,Math.floor(snapshot.source_rows*.75)))return missing('invalid_counts');
 if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(snapshot.checked_at_utc))return missing('invalid_snapshot_time');
 const retrievedAt=new Date(snapshot.checked_at_utc).toISOString();
 const ids=new Set();
 for(const p of snapshot.products){
 if(typeof p.energy_star_unique_id!=='string'||!/^\d+$/.test(p.energy_star_unique_id)||ids.has(p.energy_star_unique_id)||p.source!==url||typeof p.brand!=='string'||!p.brand.trim()||typeof p.model_number!=='string'||!p.model_number.trim())return missing('invalid_identity');
 ids.add(p.energy_star_unique_id);
 }
 const entityId='catalog:epa:wati-2tfp',metric='normalized-catalog-record-count',unit='records';
 const policy={policyId:'epa-refrigeration-private-pilot-v1',sourceId:'epa-energy-star',seriesId:'wati-2tfp:normalized-count',entityId,metric,unit,sourceUrl:url,evidence:'Leivro existing count-verified refrigeration collector; candidate only',rights:{collect:'allowed',retain:'unreviewed',display:'unreviewed',export:'unreviewed'}};
 const result=observation({...policy,periodEnd:retrievedAt.slice(0,10),value:ids.size,retrievedAt},policy,asOf);
 return {schemaVersion:1,asOf,results:[{observation:result,observedAt:retrievedAt,dateBasis:'catalog retrieval date, not certification or product release date',limitation:'Normalized catalog count; not exact retail SKUs, sales, stock or energy ratings.'}],missing:[],publicEligible:false};
 }catch{return missing('invalid_catalog_vintage');}
}
