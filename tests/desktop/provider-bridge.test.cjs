'use strict';

const test=require('node:test');
const assert=require('node:assert/strict');
const os=require('node:os');
const path=require('node:path');
const {mkdtemp,readFile,rm}=require('node:fs/promises');
const {ProviderBridge}=require('../../apps/desktop/provider-bridge.cjs');

const storage={isEncryptionAvailable:()=>true,encryptString:value=>Buffer.from('protected:'+value),decryptString:value=>Buffer.from(value).toString().slice('protected:'.length)};

test('provider bridge protects connection files and requires its token',async()=>{
  const directory=await mkdtemp(path.join(os.tmpdir(),'notetaker-bridge-test-'));
  const bridge=new ProviderBridge(directory,storage);const config=await bridge.start();
  const local=`http://127.0.0.1:${bridge.port}`;const headers={'X-Notetaker-Bridge-Token':config.token,'Content-Type':'application/json'};
  try{
    assert.equal((await fetch(local+'/connections')).status,401);
    let response=await fetch(local+'/connections',{method:'POST',headers,body:JSON.stringify({provider:'openai',model:'gpt-test',api_key:'secret-not-on-disk'})});
    assert.equal(response.status,200);
    const stored=await readFile(path.join(directory,'connections','openai.connection'),'utf8');assert.equal(stored.includes('secret-not-on-disk'),false);
    response=await fetch(local+'/connections',{headers});assert.deepEqual(await response.json(),{connections:[{name:'openai/gpt-test',digest:(await bridge.read('openai')).id,size:0,provider:'openai'}]});
    response=await fetch(local+'/connections/verify',{method:'POST',headers,body:JSON.stringify({model:'openai/gpt-test'})});assert.equal(response.status,200);
    response=await fetch(local+'/connections/openai',{method:'DELETE',headers});assert.equal(response.status,200);
    assert.deepEqual((await (await fetch(local+'/connections',{headers})).json()),{connections:[]});
  }finally{await bridge.close();await rm(directory,{recursive:true,force:true});}
});
