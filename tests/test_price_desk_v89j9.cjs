'use strict';
const assert=require('node:assert/strict'),test=require('node:test'),fs=require('node:fs'),path=require('node:path');
const src=fs.readFileSync(path.join(__dirname,'../v4.js'),'utf8');
const begin=src.indexOf('function officialEuronextQuoteUrl('),end=src.indexOf('async function licensedPricePage(',begin);
assert.ok(begin>=0&&end>begin);
const official=Function(src.slice(begin,end)+'\nreturn officialEuronextQuoteUrl;')();
test('link exact Euronext ISIN and exchange without needing a quote licence',()=>{
 assert.equal(official({mic:'XOSL',isin:'NO0010096985'}),'https://live.euronext.com/en/product/equities/NO0010096985-XOSL');
 assert.equal(official({mic:'XPAR',isin:'FR0000120271'}),'https://live.euronext.com/en/product/equities/FR0000120271-XPAR');
});
test('refuse unsafe or unsupported stock exchange quote links',()=>{
 for(const row of [{mic:'XSTO',isin:'NO0010096985'},{mic:'XOSL',isin:'wrong'},{mic:'XPAR',isin:'FR0000120271/../'},{mic:null,isin:'FR0000120271'},null])assert.equal(official(row),null);
});
test('price workspace does not lead with archive gaps',()=>{
 assert.ok(src.includes("featuredMonitored=monitored.slice(0,30)"));
 assert.ok(src.includes("Latest stock prices"));
 assert.ok(src.includes("Browse all '+monitored.length+' monitored listings"));
 assert.ok(src.includes("Exchange onboarding progress"));
 const html=fs.readFileSync(path.join(__dirname,'../price-history.html'),'utf8');
 assert.ok(html.includes('Stock prices &amp; history.'));
});
