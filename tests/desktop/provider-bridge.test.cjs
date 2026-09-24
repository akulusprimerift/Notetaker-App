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
  const bridge=new ProviderBridge(directory,storage,{fetch:async()=>new Response(JSON.stringify({data:[{id:'gpt-test'}]}))});const config=await bridge.start();
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

test('API key discovery lists text models, preserves old credentials on failure, and fences replacements',async()=>{
  const directory=await mkdtemp(path.join(os.tmpdir(),'notetaker-api-test-'));
  let valid=true;
  const bridge=new ProviderBridge(directory,storage,{fetch:async()=>valid?new Response(JSON.stringify({data:[{id:'gpt-test'},{id:'gpt-second'},{id:'gpt-audio'},{id:'text-embedding-test'}]})):new Response('{}',{status:401})});
  try{
    await bridge.save({provider:'openai',api_key:'test-key'});
    const rows=await bridge.inventory();assert.deepEqual(rows.map(row=>row.name),['openai/gpt-second','openai/gpt-test']);
    await bridge.verify({model:'openai/gpt-test',digest:rows[0].digest});
    valid=false;await assert.rejects(bridge.save({provider:'openai',api_key:'invalid'}),/validate this API key/);
    assert.equal((await bridge.read('openai')).api_key,'test-key');
    valid=true;await bridge.save({provider:'openai',api_key:'replacement'});
    await assert.rejects(bridge.verify({model:'openai/gpt-test',digest:rows[0].digest}),/connection changed/);
  }finally{await rm(directory,{recursive:true,force:true});}
});

test('ChatGPT browser login saves only after paid account verification and model discovery',async()=>{
  const directory=await mkdtemp(path.join(os.tmpdir(),'notetaker-login-test-'));
  let plan='plus',success=true,closed=0,opened='';
  const bridge=new ProviderBridge(directory,storage,{codexExecutable:'bundled-client.exe',openExternal:async url=>{opened=url;},accountClient:()=>({
    initialize:async()=>{},notification:async()=>({success,loginId:'test-login'}),
    request:async method=>method==='account/login/start'?{loginId:'test-login',authUrl:'https://auth.openai.com/authorize?test=1'}:{account:{type:'chatgpt',planType:plan}},
    models:async()=>['gpt-test','gpt-second'],close:()=>closed++,
  })});
  try{
    plan='free';await assert.rejects(bridge.signIn('chatgpt'),/paid ChatGPT/);assert.equal(await bridge.read('chatgpt'),null);
    success=false;await assert.rejects(bridge.signIn('chatgpt'),/not completed/);
    success=true;plan='plus';await bridge.signIn('chatgpt');assert.match(opened,/^https:\/\/auth.openai.com\//);assert.equal((await bridge.inventory()).length,2);
    const previous=await bridge.read('chatgpt');
    await assert.rejects(bridge.signIn('chatgpt'),/Disconnect ChatGPT/);assert.equal((await bridge.read('chatgpt')).id,previous.id);assert.equal(closed,3);
    await assert.rejects(bridge.signIn('claude-subscription'),/Anthropic approval/);
    for(const paidPlan of ['go','prolite','edu_plus','business']){await bridge.remove('chatgpt');plan=paidPlan;await bridge.signIn('chatgpt');assert.equal((await bridge.inventory()).length,2);}
  }finally{await rm(directory,{recursive:true,force:true});}
});

test('login URLs reject arbitrary domains, credentials, ports and non-HTTPS schemes',()=>{
  const {loginUrl}=require('../../apps/desktop/account-client.cjs');
  for(const url of ['file:///C:/test','http://auth.openai.com','https://auth.openai.com.evil.test','https://user@auth.openai.com','https://auth.openai.com:444'])assert.throws(()=>loginUrl(url));
  assert.equal(loginUrl('https://auth.openai.com/authorize'),'https://auth.openai.com/authorize');
});

test('account protocol closes pending requests on clean early exit',async()=>{
  const {AccountClient}=require('../../apps/desktop/account-client.cjs');
  const client=new AccountClient(process.execPath,['-e','process.exit(0)'],{});
  await assert.rejects(client.initialize(),/closed before finishing/);
  assert.equal(client.closed,true);
});

test('Claude API discovery follows pagination without exposing keys',async()=>{
  const directory=await mkdtemp(path.join(os.tmpdir(),'notetaker-pagination-test-'));
  const urls=[];
  const bridge=new ProviderBridge(directory,storage,{fetch:async url=>{
    urls.push(url);return new Response(JSON.stringify(urls.length===1?{data:[{id:'claude-a'}],has_more:true,last_id:'claude-a'}:{data:[{id:'claude-b'}],has_more:false}));
  }});
  try{
    await bridge.save({provider:'anthropic',api_key:'private-test-key'});
    assert.equal((await bridge.inventory()).length,2);assert.match(urls[1],/after_id=claude-a/);
    assert.equal(JSON.stringify(await bridge.inventory()).includes('private-test-key'),false);
  }finally{await rm(directory,{recursive:true,force:true});}
});

test('concurrent disconnect cannot race an unfinished key validation',async()=>{
  const directory=await mkdtemp(path.join(os.tmpdir(),'notetaker-race-test-'));
  let release,entered;
  const started=new Promise(resolve=>entered=resolve);
  const bridge=new ProviderBridge(directory,storage,{fetch:()=>{entered();return new Promise(resolve=>release=()=>resolve(new Response(JSON.stringify({data:[{id:'gpt-test'}]}))));}});
  const config=await bridge.start(),local=`http://127.0.0.1:${bridge.port}`;
  const headers={'X-Notetaker-Bridge-Token':config.token,'Content-Type':'application/json'};
  try{
    const saving=fetch(local+'/connections',{method:'POST',headers,body:JSON.stringify({provider:'openai',api_key:'test'})});
    await started;
    assert.equal((await fetch(local+'/connections/openai',{method:'DELETE',headers})).status,409);
    release();assert.equal((await saving).status,200);
    assert.equal((await fetch(local+'/connections/openai',{method:'DELETE',headers})).status,200);
  }finally{release?.();await bridge.close();await rm(directory,{recursive:true,force:true});}
});

test('subscription catalog includes hidden models across every page',async()=>{
  const {AccountClient}=require('../../apps/desktop/account-client.cjs');
  const seen=[];
  const models=await AccountClient.prototype.models.call({request:async(method,params)=>{
    seen.push(params);return params.cursor?{data:[{model:'gpt-hidden',hidden:true}],nextCursor:null}:{data:[{model:'gpt-first'}],nextCursor:'page-two'};
  }});
  assert.deepEqual(models,['gpt-first','gpt-hidden']);assert.ok(seen.every(p=>p.includeHidden===true));
});

test('refresh preserves credentials and disconnect revokes both subscriptions even with missing clients',async()=>{
  const directory=await mkdtemp(path.join(os.tmpdir(),'notetaker-disconnect-test-'));
  const bridge=new ProviderBridge(directory,storage,{processResult:async()=>{throw new Error('missing executable');},accountClient:()=>({initialize:async()=>{},request:async()=>({account:{type:'chatgpt',planType:'plus'}}),models:async()=>['gpt-new','gpt-hidden'],close:async()=>{}})});
  try{
    for(const provider of ['chatgpt','claude-subscription']){
      await bridge.write(provider,{provider,model:'gpt-old',id:'original-digest',executable:'missing.exe'});
      if(provider==='chatgpt'){
        await bridge.refresh(provider);assert.equal((await bridge.read(provider)).id,'original-digest');
        await bridge.verify({model:'chatgpt/gpt-hidden',digest:'original-digest'});
        await assert.rejects(bridge.verify({model:'chatgpt/gpt-old'}),/changed/);
      }
      const result=await bridge.signOut(provider);assert.match(result.notice,/Disconnected/);
      assert.equal(await bridge.read(provider),null);
      assert.deepEqual(await bridge.signOut(provider),{provider});
    }
  }finally{await rm(directory,{recursive:true,force:true});}
});


test('authenticated bridge delivers a preview while provider completion is held',async()=>{
  const directory=await mkdtemp(path.join(os.tmpdir(),'notetaker-stream-test-'));
  let finish;
  const bridge=new ProviderBridge(directory,storage,{fetch:async()=>new Response(new ReadableStream({start(controller){
    const send=value=>controller.enqueue(new TextEncoder().encode('data: '+JSON.stringify(value)+'\n\n'));
    send({choices:[{delta:{content:'{"text":"Growing'}}]});
    finish=()=>{send({choices:[{delta:{content:' notes"}'},finish_reason:'stop'}]});controller.close();};
  }}))});
  const config=await bridge.start();
  try{
    await bridge.write('openai',{provider:'openai',model:'test',models:['test'],id:'digest',api_key:'fake'});
    const response=await fetch(`http://127.0.0.1:${bridge.port}/connections/generate`,{method:'POST',headers:{'Content-Type':'application/json','X-Notetaker-Bridge-Token':config.token},body:JSON.stringify({model:'openai/test',digest:'digest',messages:[{role:'user',content:'synthetic'}],stream:true})});
    const reader=response.body.getReader();
    const first=new TextDecoder().decode((await reader.read()).value);
    assert.equal(JSON.parse(first.trim()).raw,'{"text":"Growing');
    finish();finish=null;
    let rest='';while(true){const part=await reader.read();if(part.done)break;rest+=new TextDecoder().decode(part.value);}
    const result=rest.trim().split('\n').map(JSON.parse).at(-1);
    assert.equal(result.type,'result');assert.equal(result.raw,'{"text":"Growing notes"}');
  }finally{finish?.();await bridge.close();await rm(directory,{recursive:true,force:true});}
});
