import {createRequire} from "node:module";
import {test} from "node:test";
import assert from "node:assert/strict";
const require=createRequire(import.meta.url);
const {sectionId}=require("../company-experience-v94.js");
test("only seven known research section ids are allowed",()=>{
 const a=["chart","financials","filings","peers","events","drivers","identity"];
 assert.deepEqual(a.map(sectionId),a.map(key=>"sw94-company-"+key));
});
test("unknown section names cannot form arbitrary navigation targets",()=>{
 for(const key of ["ownership-pilot","__proto__","../../admin","<script>","chart]",""])
   assert.equal(sectionId(key),null);
 assert.equal(sectionId(null),null);
 assert.equal(sectionId(42),null);
});
test("navigation label/id mappings are stable and distinct",()=>{
 const a=["chart","financials","filings","peers","events","drivers","identity"];
 assert.equal(new Set(a.map(sectionId)).size,7);
});
