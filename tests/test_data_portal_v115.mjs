import test from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const load=createRequire(import.meta.url)('../brand/data-portal.js');
const row={
 id:'shipping',title:'Shipping and freight indicators',
 category:'Maritime',description:'Sourced indicators',
 sourceUrl:'https://www.ams.usda.gov/services/transportation-analysis',
 rights:'Source-specific redistribution permission required',
 commercialStatus:'Agreement and source-rights review required',
 count:328,countUnit:'indexed observations / records',
 kind:'Dated indicators',status:'selected series connected; broader rights pending',
 fields:['seriesId','date','value','unit','sourceUrl']
};
test('V115 schema preview is descriptive and does not imply active delivery',()=>{
 const s=JSON.parse(load.schemaPreview(row));
 assert.equal(s.datasetId,'shipping');
 assert.equal(s.schemaStatus,'proposed metadata');
 assert.equal(s.apiAvailable,false);
 assert.equal(s.commercialRedistributionApproved,false);
 assert.equal(s.latestObservationTime,null);
 assert.equal(s.deliveryFrequency,null);
 assert.deepEqual(s.sampleRecords,[]);
 assert.deepEqual(s.fields,row.fields);
 assert.equal(s.observationCount,328);
 assert.match(s.notice,/not a sample record or active API/i);
});
test('V115 download does not leak underlying market samples or licensed bars',()=>{
 const fake={...row,records:[{company:'ABCD',price:999999,apiKey:'secret'}],
      history:[{date:'2026-11-20',close:123456}]};
 const schema=load.schemaPreview(fake);
 const catalog=load.exportMetadata([fake]);
 assert.doesNotMatch(schema,/"price":|999999|123456|"apiKey":/);
 assert.doesNotMatch(catalog,/"history":|999999|123456|"apiKey":/);
 assert.match(catalog,/metadata only/i);
});
test('V115 inquiries name selected product without accepting injected header breaks',()=>{
 const mail=load.inquiryLink({...row,title:'Freight\r\nBcc:evil@example.com'});
 assert.ok(mail.startsWith('mailto:vidar@nordl.dev?subject='));
 const payload=decodeURIComponent(mail);
 assert.match(payload,/Freight  Bcc:evil@example.com/);
 assert.doesNotMatch(mail,/\r|\n/);
 assert.match(payload,/Intended use/);
 assert.match(payload,/Redistribution|redistribution/);
});
test('V115 product catalog still excludes unknown and non-HTTPS sources',()=>{
 const data={datasets:[
   {id:'shipping',title:'Ships',sourceUrl:'https://www.ams.usda.gov/services/transportation-analysis',accessPolicy:'Review'},
   {id:'company-financials',title:'Financials',sourceUrl:'javascript:alert(1)',accessPolicy:'Review'},
   {id:'unknown-private',title:'Unknown',sourceUrl:'https://example.com',accessPolicy:'Review'}]};
 const records=[{id:'other',records:100},{id:'shipping-licensed-private',records:999999}];
 const rows=load.catalog(data,{datasets:records},{});
 assert.equal(rows.length,1);
 assert.equal(rows[0].id,'shipping');
 assert.equal(rows[0].count,null);
 assert.match(rows[0].commercialStatus,/review required/);
});
