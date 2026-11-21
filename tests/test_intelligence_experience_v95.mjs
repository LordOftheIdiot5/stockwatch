import {createRequire} from "node:module";
import {test} from "node:test";
import assert from "node:assert/strict";
const require=createRequire(import.meta.url);
const {legend,disclaimer}=require("../intelligence-experience-v95.js");
test("graph legend names typed evidence without inventing exchange prices",()=>{
 const rows=legend();
 assert.equal(rows.length,3);
 assert.deepEqual(rows.map(x=>x[0]),["Selected listing","Relationship evidence","Context and peers"]);
 assert.ok(rows.every(row=>row.length===2&&row.every(v=>typeof v==="string"&&v.length>5)));
});
test("legend does not label a peer or instrument identity as corporate cash flow",()=>{
 const words=legend().flat().join(" ").toLowerCase();
 assert.match(words,/identifier|instrument|classification/);
 assert.ok(!words.includes("cash transferred"));
});
test("disclaimer explicitly rejects unverified ownership and money flow",()=>{
 const d=disclaimer().toLowerCase();
 assert.match(d,/do not prove/);
 assert.match(d,/supplier revenue/);
 assert.match(d,/ownership/);
 assert.match(d,/investment flows/);
});
