'use strict';
const {spawn}=require('node:child_process');
const owned=new Set();
function killOwned(child,platform=process.platform,kill=process.kill.bind(process)) {
  if(platform==='darwin'){
    if(!Number.isSafeInteger(child.pid)||child.pid<=0)return;
    try{kill(-child.pid,'SIGKILL');}catch(error){if(error.code!=='ESRCH')throw error;}
  }else if(child.exitCode===null)child.kill();
}
function spawnOwned(executable,args,options) {
  const child=spawn(executable,args,{...options,detached:process.platform==='darwin'});
  owned.add(child);
  child.once('error',()=>owned.delete(child));
  child.once('exit',()=>{owned.delete(child);if(process.platform==='darwin')killOwned(child);});
  return child;
}
function closeOwned(){for(const child of owned)killOwned(child);}
module.exports={spawnOwned,killOwned,closeOwned};
