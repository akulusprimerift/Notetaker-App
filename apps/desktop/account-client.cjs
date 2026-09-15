'use strict';

const {spawn}=require('node:child_process');
const readline=require('node:readline');

// Only provider-owned HTTPS login pages may leave the desktop host.
function loginUrl(value) {
  const url=new URL(value);
  if(url.protocol!=='https:'||!['auth.openai.com','chatgpt.com','auth0.openai.com'].includes(url.hostname)||url.username||url.password||url.port)
    throw new Error('The provider returned an unsupported sign-in address.');
  return url.href;
}

class AccountClient {
  constructor(executable,args,options) {
    this.pending=new Map();this.waiters=new Map();this.sequence=0;this.closed=false;
    this.child=spawn(executable,args,{...options,windowsHide:true,stdio:['pipe','pipe','ignore']});
    this.exited=new Promise(resolve=>this.child.once('close',resolve));
    this.reader=readline.createInterface({input:this.child.stdout});
    this.reader.on('line',line=>{
      if(line.length>2_000_000){this.close(new Error('The provider returned too much data.'));return;}
      let event;try{event=JSON.parse(line);}catch{this.close(new Error('The provider returned invalid data.'));return;}
      if(event.id!==undefined&&event.method){this.close(new Error('The account helper requested an unsupported action.'));return;}
      if(event.id!==undefined){const entry=this.pending.get(event.id);if(entry){this.pending.delete(event.id);event.error?entry.reject(new Error('The provider could not complete this account request.')):entry.resolve(event.result);}}
      else if(event.method){const entry=this.waiters.get(event.method);if(entry){this.waiters.delete(event.method);entry.resolve(event.params);}}
    });
    this.child.once('error',()=>this.close(new Error('The bundled sign-in helper could not start. Reinstall Notetaker.')));
    this.child.once('exit',()=>this.close(new Error('The sign-in helper closed before finishing.')));
    this.child.stdin.on('error',()=>this.close(new Error('The sign-in helper disconnected.')));
  }
  deferred(map,key,timeout) {
    return new Promise((resolve,reject)=>{
      if(this.closed){reject(new Error('The sign-in helper is closed.'));return;}
      const timer=setTimeout(()=>{map.delete(key);reject(new Error('Sign-in timed out. Try linking your account again.'));},timeout);
      map.set(key,{resolve:value=>{clearTimeout(timer);resolve(value);},reject:error=>{clearTimeout(timer);reject(error);}});
    });
  }
  request(method,params={}) {
    const id=++this.sequence,result=this.deferred(this.pending,id,30_000);
    if(!this.closed)this.child.stdin.write(JSON.stringify({id,method,params})+'\n');
    return result;
  }
  notification(method,timeout=180_000){return this.deferred(this.waiters,method,timeout);}
  async initialize(){await this.request('initialize',{clientInfo:{name:'notetaker',version:'0.1.0'}});this.child.stdin.write('{"method":"initialized"}\n');}
  async models(){
    const models=[];let cursor=null;const seen=new Set();
    do{
      const result=await this.request('model/list',{limit:100,includeHidden:false,cursor});
      if(!Array.isArray(result?.data))throw new Error('The provider returned an invalid model list.');
      models.push(...result.data.map(row=>row.model));cursor=result.nextCursor;
      if(cursor&&seen.has(cursor))throw new Error('The provider returned a repeated model page.');
      seen.add(cursor);
      if(models.length>2000)throw new Error('The provider returned too many models.');
    }while(cursor);
    return models;
  }
  close(error=new Error('Account request cancelled.')) {
    if(this.closed)return this.exited;this.closed=true;
    for(const map of [this.pending,this.waiters]){for(const entry of map.values())entry.reject(error);map.clear();}
    this.reader.close();if(this.child.exitCode===null)this.child.kill();
    return this.exited;
  }
}

module.exports={AccountClient,loginUrl};
