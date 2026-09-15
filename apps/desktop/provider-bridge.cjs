'use strict';

const {createServer} = require('node:http');
const {timingSafeEqual} = require('node:crypto');
const {randomUUID} = require('node:crypto');
const {mkdtemp, mkdir, readFile, rename, rm, writeFile} = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const {spawn} = require('node:child_process');
const readline = require('node:readline');
const {AccountClient,loginUrl}=require('./account-client.cjs');

const PROVIDERS = ['openai', 'anthropic', 'chatgpt', 'claude-subscription'];
const MODEL = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$/;
const SUBSCRIPTIONS = new Set(['chatgpt', 'claude-subscription']);
const BLOCKED_ENV = ['OPENAI_', 'ANTHROPIC_', 'CLAUDE_', 'CODEX_', 'NOTETAKER_', 'AWS_', 'AZURE_', 'GOOGLE_'];
const CODEX_DISABLED = ['shell_tool', 'unified_exec', 'code_mode', 'code_mode_host', 'view_image',
  'computer_use', 'browser_use', 'browser_use_external', 'browser_use_full_cdp_access', 'in_app_browser',
  'apps', 'plugins', 'plugin_sharing', 'remote_plugin', 'hooks', 'multi_agent', 'multi_agent_v2',
  'image_generation', 'artifact', 'skill_search', 'workspace_dependencies', 'memories', 'shell_snapshot'];

class BridgeError extends Error {
  constructor(code, message, status=422) {super(message);this.code=code;this.status=status;}
}

function providerName(provider) {
  if (!PROVIDERS.includes(provider)) throw new BridgeError('provider_invalid', 'Choose a supported provider.');
  return provider;
}

function safeEnvironment(provider, directory) {
  const env = {...process.env};
  for (const key of Object.keys(env)) if (BLOCKED_ENV.some(prefix => key.toUpperCase().startsWith(prefix))) delete env[key];
  if (provider === 'chatgpt') env.CODEX_HOME = path.join(directory, 'chatgpt-client');
  if (provider === 'claude-subscription') {
    env.CLAUDE_CONFIG_DIR = path.join(directory, 'claude-subscription-client');
    env.CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC = '1';
    env.DISABLE_AUTOUPDATER = '1';
  }
  return env;
}

function sendJson(response, status, body) {
  const encoded = JSON.stringify(body);
  response.writeHead(status, {'Content-Type':'application/json; charset=utf-8', 'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff'});
  response.end(encoded);
}

async function body(request) {
  let size = 0, text = '';
  for await (const chunk of request) {
    size += chunk.length;
    if (size > 2_500_000) throw new BridgeError('request_too_large', 'The provider request is too large.', 413);
    text += chunk;
  }
  if (!text) return {};
  try {return JSON.parse(text);} catch {throw new BridgeError('invalid_request', 'The provider request was invalid.');}
}

function processResult(executable, args, options={}, timeout=30_000) {
  return new Promise((resolve, reject) => {
    const child = spawn(executable, args, {cwd:options.cwd, env:options.env, windowsHide:true, stdio:['ignore','pipe','ignore']});
    let output = '', timer = setTimeout(() => {child.kill();reject(new BridgeError('provider_timeout', 'The provider client took too long to respond.'));}, timeout);
    child.stdout.on('data', chunk => {output += chunk.toString(); if (output.length > 2_000_000) {child.kill();clearTimeout(timer);reject(new BridgeError('invalid_output', 'The provider returned too much output.'));}});
    child.once('error', error => {clearTimeout(timer);reject(new BridgeError('subscription_client_unavailable', error.code === 'ENOENT' ? 'The selected official provider client could not be started.' : 'The official provider client could not be started.'));});
    child.once('exit', code => {clearTimeout(timer);if(code===0)resolve(output);else reject(new BridgeError('provider_authentication', 'The official provider client did not complete the request.'));});
  });
}

function codexArgs(executable) {
  const args = ['app-server'];
  for (const name of CODEX_DISABLED) args.push('-c', `features.${name}=false`);
  args.push('-c', 'web_search="disabled"', '-c', 'approval_policy="never"', '-c', 'sandbox_mode="read-only"',
    '-c', 'cli_auth_credentials_store="keyring"', '-c', 'history.persistence="none"', '-c', 'project_doc_max_bytes=0');
  return args;
}

function codexGenerate(row, messages, directory) {
  return new Promise(async (resolve, reject) => {
    let cwd;
    try {cwd=await mkdtemp(path.join(os.tmpdir(), 'notetaker-context-'));} catch {reject(new BridgeError('provider_unavailable', 'The temporary provider workspace could not be created.'));return;}
    const env=safeEnvironment('chatgpt', directory);
    const child=spawn(row.executable, codexArgs(row.executable), {cwd,env,windowsHide:true,stdio:['pipe','pipe','ignore']});
    const reader=readline.createInterface({input:child.stdout});
    let text='', final='', finished=false, timer=setTimeout(()=>finish(new BridgeError('provider_timeout','The ChatGPT client took too long to respond.')),600_000);
    const finish=(error, value)=>{if(finished)return;finished=true;clearTimeout(timer);reader.close();if(child.exitCode===null)child.kill();void rm(cwd,{recursive:true,force:true});if(error)reject(error);else resolve(value);};
    const send=value=>{try{child.stdin.write(JSON.stringify(value)+'\n');}catch{finish(new BridgeError('subscription_client_unavailable','The ChatGPT client closed unexpectedly.'));}};
    reader.on('line', line=>{
      let event;try{event=JSON.parse(line);}catch{finish(new BridgeError('subscription_client_unavailable','The ChatGPT client returned invalid output.'));return;}
      if(event.error){finish(new BridgeError('provider_authentication','The ChatGPT subscription is not available to Notetaker.'));return;}
      if(event.method&&event.id!==undefined){finish(new BridgeError('unexpected_tool_request','The subscription provider requested an unsupported action.'));return;}
      if(event.id===1){send({method:'initialized'});send({id:2,method:'account/read',params:{}});}
      else if(event.id===2){if(event.result?.account?.type!=='chatgpt'){finish(new BridgeError('provider_authentication','Sign in to the ChatGPT subscription client first.'));return;}send({id:3,method:'thread/start',params:{model:row.model,cwd,ephemeral:true,approvalPolicy:'never',sandbox:'read-only'}});}
      else if(event.id===3){const thread=event.result?.thread?.id;if(!thread){finish(new BridgeError('provider_unavailable','The ChatGPT subscription did not open a note session.'));return;}send({id:4,method:'turn/start',params:{threadId:thread,input:[{type:'text',text:messages.map(message=>message.content).join('\n\n')}]}});}
      else if(event.method==='item/agentMessage/delta')text+=event.params?.delta||'';
      else if(event.method==='item/completed'&&event.params?.item?.type==='agentMessage')final=event.params.item.text||'';
      else if(event.method==='turn/completed'){if(event.params?.turn?.status!=='completed')finish(new BridgeError('provider_limit_or_failure','The ChatGPT subscription stopped before completing the note request.'));else finish(null,{raw:final||text,metrics:{client:'codex-app-server',billing:'subscription'}});}
    });
    child.once('error', error=>finish(new BridgeError('subscription_client_unavailable',error.code==='ENOENT'?'The selected Codex client could not be started.':'The Codex client could not be started.')));
    child.once('exit', code=>{if(!finished&&code!==0)finish(new BridgeError('provider_authentication','The ChatGPT subscription client did not complete the request.'));});
    send({id:1,method:'initialize',params:{clientInfo:{name:'notetaker',title:'Notetaker',version:'0.4.0'}}});
  });
}

async function claudeGenerate(row, messages, directory) {
  const cwd=await mkdtemp(path.join(os.tmpdir(), 'notetaker-context-'));
  const env=safeEnvironment('claude-subscription', directory);
  try {
    let auth;
    try {auth=JSON.parse(await processResult(row.executable,['auth','status'],{cwd,env},30_000));} catch {throw new BridgeError('provider_authentication','Sign in to the Claude subscription client first.');}
    if(auth.authMethod!=='claude.ai') throw new BridgeError('provider_authentication','Sign in to the Claude subscription client first.');
    const args=[row.executable,'-p','--model',row.model,'--output-format','stream-json','--verbose','--include-partial-messages','--tools','','--disallowedTools','*','--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--safe-mode','--setting-sources','','--settings','{"disableAllHooks":true}','--no-session-persistence','--no-chrome','--max-turns','1'];
    const result=await new Promise((resolve,reject)=>{
      const child=spawn(args[0],args.slice(1),{cwd,env,windowsHide:true,stdio:['pipe','pipe','ignore']});
      const reader=readline.createInterface({input:child.stdout});let text='',timer=setTimeout(()=>{child.kill();reject(new BridgeError('provider_timeout','The Claude subscription took too long to respond.'));},600_000),done=false;
      const finish=(error,value)=>{if(done)return;done=true;clearTimeout(timer);reader.close();if(child.exitCode===null)child.kill();if(error)reject(error);else resolve(value);};
      reader.on('line',line=>{let event;try{event=JSON.parse(line);}catch{finish(new BridgeError('subscription_client_unavailable','The Claude client returned invalid output.'));return;}if(event.type==='stream_event'){const part=event.event||{};if(part.type==='content_block_start'&&part.content_block?.type==='tool_use')finish(new BridgeError('unexpected_tool_request','The subscription provider requested an unsupported action.'));text+=part.delta?.text||'';}if(event.type==='result'){if(event.is_error||event.subtype!=='success')finish(new BridgeError('provider_limit_or_failure','The Claude subscription stopped before completing the note request.'));else finish(null,{raw:event.result||text,metrics:{client:'claude-code',billing:'subscription',usage:event.usage||{}}});}});
      child.once('error',error=>finish(new BridgeError('subscription_client_unavailable',error.code==='ENOENT'?'The selected Claude client could not be started.':'The Claude client could not be started.')));
      child.once('exit',code=>{if(!done&&code!==0)finish(new BridgeError('provider_authentication','The Claude subscription client did not complete the request.'));});
      child.stdin.end(messages.map(message=>message.content).join('\n\n'));
    });
    return result;
  } finally {await rm(cwd,{recursive:true,force:true});}
}

class ProviderBridge {
  constructor(userData, safeStorage, options={}) {this.options=options;this.busy=new Set();this.clients=new Set();this.userData=userData;this.safeStorage=safeStorage;this.directory=path.join(userData,'connections');this.server=null;this.port=0;this.token=randomUUID()+randomUUID();}
  file(provider){providerName(provider);return path.join(this.directory,provider+'.connection');}
  async read(provider) {
    providerName(provider);
    let encoded;try {encoded=await readFile(this.file(provider),'utf8');} catch(error) {if(error.code==='ENOENT')return null;throw new BridgeError('provider_connection_invalid','This provider connection is unavailable. Connect it again.');}
    try {const row=JSON.parse(this.safeStorage.decryptString(Buffer.from(encoded,'base64')));if(row.provider!==provider||!MODEL.test(row.model)||(row.models&&(!Array.isArray(row.models)||row.models.some(model=>typeof model!=='string'||!MODEL.test(model)))))throw new Error();return row;}catch{throw new BridgeError('provider_connection_invalid','This provider connection is unavailable. Connect it again.');}
  }
  async write(provider,row) {
    if(!this.safeStorage.isEncryptionAvailable())throw new BridgeError('protected_storage_unavailable','Windows protected storage is unavailable. Restart Notetaker and try again.',503);
    await mkdir(this.directory,{recursive:true});
    const temporary=this.file(provider)+'.'+randomUUID()+'.pending';
    const encoded=this.safeStorage.encryptString(JSON.stringify(row)).toString('base64');
    try {await writeFile(temporary,encoded,{flag:'wx'});await rename(temporary,this.file(provider));} finally {await rm(temporary,{force:true});}
  }
  async inventory() {
    const connections=[];
    for(const provider of PROVIDERS){try{const row=await this.read(provider);if(row)for(const model of row.models||[row.model])connections.push({name:provider+'/'+model,digest:row.id,size:0,provider});}catch{/* Invalid connections remain hidden until replaced. */}}
    return connections;
  }
  async save(input) {
    const provider=providerName(input.provider),model=String(input.model||'');
    if(SUBSCRIPTIONS.has(provider))throw new BridgeError('provider_connection_invalid','Use Link account to connect a subscription.');
    if(model&&!MODEL.test(model))throw new BridgeError('provider_connection_invalid','Enter a valid model ID from the provider.');
    const apiKey=String(input.api_key||'');
    if(!apiKey||apiKey.length>8192||/\s/.test(apiKey))throw new BridgeError('provider_connection_invalid','Enter an API key without spaces.');
    // Validate the key and discover models before replacing any working connection.
    const models=await this.apiModels(provider,apiKey);
    if(model&&!models.includes(model))throw new BridgeError('provider_connection_invalid','This key does not list the requested model.');
    const row={provider,model:model||models[0],models,api_key:apiKey,executable:'',id:randomUUID()};
    await this.write(provider,row);return {provider,model:row.model,digest:row.id};
  }
  async apiModels(provider,key) {
    const base=provider==='openai'?'https://api.openai.com/v1/models':'https://api.anthropic.com/v1/models';
    const headers=provider==='openai'?{Authorization:'Bearer '+key}:{'x-api-key':key,'anthropic-version':'2023-06-01'};
    const signal=AbortSignal.timeout(45_000);
    const models=[];let after='';const seen=new Set();
    do{
      let response;
      try{response=await (this.options.fetch||fetch)(base+(after?'?after_id='+encodeURIComponent(after):''),{headers,redirect:'error',signal});}
      catch{throw new BridgeError('provider_unavailable','Could not load models. Check your connection and try again.');}
      if(!response.ok)throw new BridgeError('provider_authentication',response.status===429?'The provider usage limit was reached. Try again later.':'Could not validate this API key. Check its model-list permission and billing account.');
      const text=await response.text();if(text.length>2_000_000)throw new BridgeError('invalid_output','The provider model list was too large.');
      let result;try{result=JSON.parse(text);if(!Array.isArray(result.data))throw new Error();}catch{throw new BridgeError('invalid_output','The provider returned an invalid model list.');}
      for(const item of result.data){const id=item.id;if(typeof id==='string'&&MODEL.test(id)&&(provider==='anthropic'||(/^(gpt-|o[134](?:-|$))/.test(id)&&!/(audio|realtime|transcribe|image|search|instruct|codex|pro|deep-research)/.test(id))))models.push(id);}
      after=provider==='anthropic'&&result.has_more?result.last_id:'';
      if((result.has_more&&!after)||seen.has(after)||seen.size>20)throw new BridgeError('invalid_output','The provider model list could not be completed.');
      if(after)seen.add(after);
    }while(after);
    const unique=[...new Set(models)].sort();if(!unique.length)throw new BridgeError('provider_connection_invalid','This key has no supported text models available.');return unique;
  }
  async verify(input) {const model=String(input.model||''),[provider,name]=model.split('/',2);const row=await this.read(provider);if(!row||!(row.models||[row.model]).includes(name)||(input.digest&&row.id!==input.digest))throw new BridgeError('connection_unavailable','This provider connection changed. Reconnect it and apply the model again.',503);return {digest:row.id};}
  async remove(provider) {await rm(this.file(provider),{force:true});return {provider};}
  async signIn(provider) {
    providerName(provider);
    if(provider!=='chatgpt')throw new BridgeError('provider_connection_invalid','Claude subscription linking requires Anthropic approval for this app. Connect a Claude API key instead.');
    if(await this.read(provider))throw new BridgeError('connection_exists','Disconnect ChatGPT before linking another account.');
    await mkdir(path.join(this.directory,'chatgpt-client'),{recursive:true});
    const executable=this.options.codexExecutable;
    if(!executable)throw new BridgeError('subscription_client_unavailable','The bundled ChatGPT helper is missing. Reinstall Notetaker.');
    const client=this.options.accountClient?this.options.accountClient():new AccountClient(executable,codexArgs(),{cwd:this.directory,env:safeEnvironment(provider,this.directory)});
    this.clients.add(client);
    const timer=setTimeout(()=>client.close(new Error('Sign-in timed out. Try linking your account again.')),180_000);
    try{
      await client.initialize();
      const completion=client.notification('account/login/completed');
      // Attach a rejection handler immediately while the browser is being opened.
      completion.catch(()=>{});
      const login=await client.request('account/login/start',{type:'chatgpt'});
      await this.options.openExternal(loginUrl(login.authUrl));
      const completed=await completion;
      if(!completed.success||completed.loginId!==login.loginId)throw new Error('Sign-in was not completed. Try again.');
      const result=await client.request('account/read',{}),account=result?.account;
      if(account?.type!=='chatgpt'||!['go','plus','pro','prolite','team','self_serve_business_prolite','self_serve_business_usage_based','business','ent26','enterprise_cbp_automation','enterprise_cbp_usage_based','enterprise','edu','edu_plus','edu_pro'].includes(String(account.planType).toLowerCase()))throw new Error('Link an eligible paid ChatGPT subscription to use it for notes.');
      const models=[...new Set(await client.models())].filter(model=>typeof model==='string'&&MODEL.test(model));
      if(!models.length)throw new Error('No note models are available through this subscription.');
      const row={provider,model:models[0],models,api_key:'',executable,id:randomUUID()};
      await this.write(provider,row);return {provider};
    }catch(error){try{await client.request('account/logout',{});}catch{/* The helper may already have exited. */}throw new BridgeError('provider_authentication',error.message||'Could not link your ChatGPT account.');}
    finally{clearTimeout(timer);await client.close();this.clients.delete(client);}
  }
  async signOut(provider) {const row=await this.read(provider);if(!row||!SUBSCRIPTIONS.has(provider))throw new BridgeError('provider_connection_invalid','This subscription is not connected.');const args=provider==='chatgpt'?[row.executable,'logout','-c','cli_auth_credentials_store="keyring"']:[row.executable,'auth','logout'];await processResult(args[0],args.slice(1),{cwd:this.directory,env:safeEnvironment(provider,this.directory)},30_000);await this.remove(provider);return {provider};}
  async generate(input) {
    const model=String(input.model||''),[provider,name]=model.split('/',2),row=await this.read(provider);
    if(!row||!(row.models||[row.model]).includes(name)||(input.digest&&row.id!==input.digest))throw new BridgeError('connection_unavailable','This provider connection changed. Reconnect it and apply the model again.',503);
    const messages=input.messages;if(!Array.isArray(messages)||messages.length<1||JSON.stringify(messages).length>150_000)throw new BridgeError('invalid_request','The note request was invalid.');
    if(SUBSCRIPTIONS.has(provider))return provider==='chatgpt'?codexGenerate({...row,model:name},messages,this.directory):claudeGenerate({...row,model:name},messages,this.directory);
    const headers={'Content-Type':'application/json'};let url,request;
    if(provider==='openai'){url='https://api.openai.com/v1/chat/completions';headers.Authorization='Bearer '+row.api_key;request={model:name,messages,stream:false,store:false,max_completion_tokens:6000,response_format:{type:'json_object'}};}
    else {url='https://api.anthropic.com/v1/messages';headers['x-api-key']=row.api_key;headers['anthropic-version']='2023-06-01';request={model:name,system:messages[0]?.content||'',messages:messages.slice(1),max_tokens:6000,stream:false};}
    let response;try {response=await fetch(url,{method:'POST',headers,body:JSON.stringify(request),signal:AbortSignal.timeout(600_000),redirect:'error'});} catch {throw new BridgeError('provider_unavailable','The provider could not be reached.',503);}
    if(response.status===401||response.status===403)throw new BridgeError('provider_authentication','The provider rejected this connection. Check the API key.');
    if(response.status===429)throw new BridgeError('provider_limit','The provider usage limit was reached.');
    if(!response.ok)throw new BridgeError('provider_unavailable','The provider could not complete the note request.',503);
    let result;try{const text=await response.text();if(text.length>2_000_000)throw new Error();result=JSON.parse(text);}catch{throw new BridgeError('invalid_output','The provider returned invalid note output.');}
    const raw=provider==='openai'?result.choices?.[0]?.message?.content:result.content?.[0]?.text;
    if(typeof raw!=='string'||!raw)throw new BridgeError('invalid_output','The provider returned no note content.');
    return {raw,metrics:result.usage||{}};
  }
  async handle(request,response) {
    const supplied=String(request.headers['x-notetaker-bridge-token']||'');
    const matches=supplied.length===this.token.length&&timingSafeEqual(Buffer.from(supplied),Buffer.from(this.token));
    if(!matches){sendJson(response,401,{code:'bridge_unauthorized',message:'Unauthorized provider bridge request.'});return;}
    let lockedProvider;
    try {
      const url=new URL(request.url,'http://127.0.0.1'), parts=url.pathname.split('/').filter(Boolean), input=request.method==='GET'||request.method==='DELETE'?{}:await body(request);
      if(request.method!=='GET'&&parts[0]==='connections'&&!['verify','generate'].includes(parts[1])){
        const provider=providerName(parts.length===1?input.provider:parts[1]);
        if(this.busy.has(provider))throw new BridgeError('connection_busy','An account operation is already in progress. Finish it before trying again.',409);
        this.busy.add(provider);lockedProvider=provider;
      }
      let result;
      if(request.method==='GET'&&url.pathname==='/connections')result={connections:await this.inventory()};
      else if(request.method==='POST'&&url.pathname==='/connections')result=await this.save(input);
      else if(request.method==='POST'&&url.pathname==='/connections/verify')result=await this.verify(input);
      else if(request.method==='POST'&&url.pathname==='/connections/generate')result=await this.generate(input);
      else if(parts.length===2&&parts[0]==='connections'&&request.method==='DELETE')result=await this.remove(parts[1]);
      else if(parts.length===3&&parts[0]==='connections'&&parts[2]==='sign-in'&&request.method==='POST')result=await this.signIn(parts[1]);
      else if(parts.length===3&&parts[0]==='connections'&&parts[2]==='sign-out'&&request.method==='POST')result=await this.signOut(parts[1]);
      else throw new BridgeError('not_found','The provider bridge route was not found.',404);
      sendJson(response,200,result);
    } catch(error) {const failure=error instanceof BridgeError?error:new BridgeError('provider_bridge_failure','The provider connection could not be completed.',503);sendJson(response,failure.status,{code:failure.code,message:failure.message});}finally{if(lockedProvider)this.busy.delete(lockedProvider);}
  }
  async start() {this.server=createServer((request,response)=>void this.handle(request,response));await new Promise((resolve,reject)=>{this.server.once('error',reject);this.server.listen(0,'0.0.0.0',resolve);});this.port=this.server.address().port;return {url:`http://host.docker.internal:${this.port}`,token:this.token,port:this.port};}
  async close() {for(const client of this.clients)await client.close();if(this.server)await new Promise(resolve=>this.server.close(resolve));this.server=null;}
}

module.exports={ProviderBridge,PROVIDERS,safeEnvironment,codexArgs};
