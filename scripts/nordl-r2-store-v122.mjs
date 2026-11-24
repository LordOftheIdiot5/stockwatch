// Private binding only; never exposes a public route.
export function privateR2Store(bucket){
 if(!bucket||typeof bucket.put!=='function'||typeof bucket.get!=='function')throw Error('missing_private_bucket');
 return Object.freeze({
 async putIfAbsent(key,bytes){
 if(!/^nordl\/v1\/(revisions|receipts)\/[a-f0-9]{64}\.json$/.test(key))throw Error('invalid_archive_key');
 await bucket.put(key,bytes,{onlyIf:{etagDoesNotMatch:'*'},httpMetadata:{contentType:'application/json'}});
 },
 async get(key){const object=await bucket.get(key);return object?new Uint8Array(await object.arrayBuffer()):null;}
 });
}
