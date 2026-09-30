const {test}=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const {desktopPlatform,accountExecutable,validateRuntimeTarget}=require('../../apps/desktop/platform.cjs');
const {killOwned}=require('../../apps/desktop/owned-child.cjs');

test('desktop service and helper selection separates Windows x64 and Apple Silicon',()=>{
  for(const [os,arch,service,helper] of [['win32','x64','NotetakerService.exe','codex.exe'],['darwin','arm64','NotetakerService','codex']]){
    const platform=desktopPlatform(os,arch);
    assert.equal(platform.service,service);
    assert.equal(accountExecutable({packaged:true,resources:'bundle',platform}),path.join('bundle','account-client','bin',helper));
    assert.equal(accountExecutable({packaged:false,root:'repo',platform}),path.join('repo','node_modules','@openai',platform.helperPackage,'vendor',platform.helperVendor,'bin',helper));
  }
  assert.throws(()=>desktopPlatform('darwin','x64'),/Apple Silicon/);
  assert.throws(()=>desktopPlatform('linux','x64'),/supports/);
});
test('runtime target rejects cross-platform bundles and retains legacy Windows compatibility',()=>{
  const win=desktopPlatform('win32','x64'),mac=desktopPlatform('darwin','arm64');
  const legacy={profile:'windows-postgresql-seaweed-reconciliation',files:[{path:'service/NotetakerService.exe'}]};
  validateRuntimeTarget(legacy,win);
  assert.throws(()=>validateRuntimeTarget(legacy,mac),/does not match/);
  const manifest={platform:'darwin',arch:'arm64',files:[{path:'service/NotetakerService'}]};
  validateRuntimeTarget(manifest,mac);
  assert.throws(()=>validateRuntimeTarget(manifest,win),/does not match/);
  assert.throws(()=>validateRuntimeTarget({...manifest,files:[]},mac),/missing/);
});
test('Mac helper cleanup targets only its owned group even after the leader exits',()=>{
  const signals=[];
  killOwned({pid:1234,exitCode:0},'darwin',(...args)=>signals.push(args));
  killOwned({pid:undefined},'darwin',()=>assert.fail('invalid PID'));
  assert.deepEqual(signals,[[-1234,'SIGKILL']]);
  assert.doesNotThrow(()=>killOwned({pid:1234},'darwin',()=>{throw Object.assign(new Error(),{code:'ESRCH'});}));
  let killed=false;
  killOwned({exitCode:null,kill:()=>{killed=true;}},'win32');
  assert.ok(killed);
});
