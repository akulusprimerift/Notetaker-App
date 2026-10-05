'use strict';
const fs = require('node:fs/promises');
const {createReadStream} = require('node:fs');
const path = require('node:path');
const {spawn} = require('node:child_process');
const {createHash} = require('node:crypto');

const {desktopPlatform,validateRuntimeTarget}=require('./platform.cjs');

const delay = ms=>new Promise(resolve=>setTimeout(resolve,ms));
function safeRelative(value) {
  if(typeof value!=='string'||!value||path.isAbsolute(value)||value.includes('\\')||value.split('/').some(part=>!part||part==='.'||part==='..'))
    throw new Error('Invalid bundled file path.');
  return value;
}
async function verifyBundle(root) {
  const manifest = JSON.parse(await fs.readFile(path.join(root,'runtime-manifest.json'),'utf8'));
  if(manifest.schema_version!==1||!Array.isArray(manifest.files)||!manifest.files.length)throw new Error('The bundled runtime manifest is invalid.');
  for(let index=0;index<manifest.files.length;index+=8){
    await Promise.all(manifest.files.slice(index,index+8).map(async file=>{
      const relative=safeRelative(file.path),hash=createHash('sha256');
      for await(const bytes of createReadStream(path.join(root,relative)))hash.update(bytes);
      if(hash.digest('hex')!==file.sha256)throw new Error('A bundled runtime file is damaged. Reinstall Notetaker.');
    }));
  }
  return manifest;
}

class NativeRuntime {
  constructor({resources,dataPath,libraryPath,utilityProcess,onFailure=()=>{},onProgress=()=>{},platform=desktopPlatform()}){
    Object.assign(this,{resources,dataPath,libraryPath:libraryPath||path.join(dataPath,'sqlite-library'),utilityProcess,onFailure,onProgress,platform});
    this.host=null;this.web=null;this.ready=false;this.stopping=false;
  }
  async start({speechPath='',bridgeConfig}={}){
    if(this.ready)return;
    if(this.host)throw new Error('Wait for the previous standalone workspace to stop.');
    this.stopping=false;
    this.onProgress('Checking bundled runtime files…');
    const manifest=await verifyBundle(this.resources);
    if(this.stopping)throw new Error('Standalone startup was cancelled.');
    validateRuntimeTarget(manifest,this.platform);
    const library=this.libraryPath;
    if(!path.isAbsolute(library))throw new Error('Choose an absolute library folder.');
    try{await fs.access(path.join(library,'postgres'));throw new Error('Convert this PostgreSQL library into a separate SQLite library first. Existing files were retained.');}
    catch(error){if(error.code!=='ENOENT')throw error;}
    try{await fs.access(path.join(library,'conversion.pending'));throw new Error('This library conversion is incomplete. Keep the original library and finish conversion before opening it.');}
    catch(error){if(error.code!=='ENOENT')throw error;}
    const webRoot=path.join(this.dataPath,'standalone-web',manifest.web_build_id);
    safeRelative(manifest.web_build_id);
    // A writable copy keeps Next cache and generated files outside installation.
    await fs.mkdir(webRoot,{recursive:true});
    await fs.cp(path.join(this.resources,'web'),webRoot,{recursive:true});
    if(this.stopping)throw new Error('Standalone startup was cancelled.');
    const env={...process.env};
    for(const key of Object.keys(env))if(/^(NODE_OPTIONS|NODE_PATH|ELECTRON_RUN_AS_NODE|PYTHON|NOTETAKER_)/i.test(key))delete env[key];
    const host=spawn(path.join(this.resources,'service',this.platform.service),['host'],{
      cwd:this.dataPath,env,windowsHide:true,stdio:['pipe','pipe','pipe'],
    });
    this.host=host;
    let output='';
    host.stderr.on('data',()=>{});
    try{
      await new Promise((resolve,reject)=>{
        const timer=setTimeout(()=>reject(new Error('Standalone services took too long to start.')),600000);
        const fail=error=>{clearTimeout(timer);reject(error);};
        host.once('error',fail);
        host.once('exit',()=>{this.ready=false;if(this.host===host)this.host=null;fail(new Error('The standalone services stopped. Your library was retained.'));if(!this.stopping)this.onFailure('The standalone services stopped. Reopen the app to recover.');});
        host.stdout.on('data',chunk=>{
          output+=chunk.toString();
          let end;
          while((end=output.indexOf('\n'))>=0){
            const line=output.slice(0,end);output=output.slice(end+1);
            try{const value=JSON.parse(line);if(value.status==='ready'){clearTimeout(timer);resolve();}
              else if(value.status==='progress')this.onProgress(value.message);
              else if(value.status==='failed'){fail(new Error(value.message));if(this.ready)this.onFailure(value.message);}}
            catch{/* Only structured host status is exposed. */}
          }
        });
        host.stdin.on('error',fail);
        host.stdin.write(JSON.stringify({resources:this.resources,data:library,speechPath,
          bridgeURL:bridgeConfig?`http://127.0.0.1:${bridgeConfig.port}`:'',bridgeToken:bridgeConfig?.token||''})+'\n');
      });
      this.web=this.utilityProcess.fork(path.join(webRoot,'apps/web/server.js'),[],{
        cwd:webRoot,env:{...env,NODE_ENV:'production',HOSTNAME:'127.0.0.1',PORT:'3000',NEXT_TELEMETRY_DISABLED:'1'},
        stdio:'pipe',serviceName:'Notetaker workspace',
      });
      this.web.stdout.on('data',()=>{});this.web.stderr.on('data',()=>{});
      let exited=false;
      this.web.once('exit',()=>{exited=true;this.ready=false;if(!this.stopping)this.onFailure('The workspace server stopped. Saved audio and drafts were retained.');});
      for(let attempt=0;attempt<120;attempt++){
        if(exited||!this.host)throw new Error('A standalone service stopped during startup.');
        try{const response=await fetch('http://127.0.0.1:3000/api/health',{signal:AbortSignal.timeout(1500),redirect:'error'});
          if(response.ok&&(await response.json()).status==='ok'){this.ready=true;return;}}
        catch{/* Startup. */}
        await delay(500);
      }
      throw new Error('The bundled workspace did not become ready.');
    }catch(error){await this.stop();throw error;}
  }
  async stop(){
    this.stopping=true;this.ready=false;
    if(this.web){this.web.kill();this.web=null;}
    const host=this.host;
    if(host){
      if(host.exitCode===null&&host.signalCode===null){
        await new Promise(resolve=>{
          const done=()=>{clearTimeout(timer);host.removeListener('exit',done);resolve();};
          const timer=setTimeout(done,60000);
          host.once('exit',done);
          host.stdin.end();
        });
        if(host.exitCode===null&&host.signalCode===null)host.kill();
      }
      this.host=null;
    }
  }
}
module.exports={NativeRuntime,safeRelative,verifyBundle};
