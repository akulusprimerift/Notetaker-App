// Read-only protocol handshake in a fresh isolated profile. No login or inference.
const {mkdtemp,mkdir,rm}=require('node:fs/promises');
const os=require('node:os');
const path=require('node:path');
const assert=require('node:assert/strict');
const {AccountClient}=require('../../apps/desktop/account-client.cjs');
const {safeEnvironment,codexArgs}=require('../../apps/desktop/provider-bridge.cjs');
(async()=>{
  const directory=await mkdtemp(path.join(os.tmpdir(),'notetaker-account-handshake-'));
  const executable=process.env.NOTETAKER_ACCOUNT_HELPER||path.resolve('node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe');
  await mkdir(path.join(directory,'chatgpt-client'));
  const client=new AccountClient(executable,codexArgs(),{cwd:directory,env:safeEnvironment('chatgpt',directory)});
  try{
    await client.initialize();
    const result=await client.request('account/read',{});
    assert.equal(result.account,null);
    console.log('Bundled helper: initialize/account-read protocol passed in a fresh signed-out profile.');
  }finally{await client.close();await rm(directory,{recursive:true,force:true});}
})().catch(error=>{console.error(error);process.exitCode=1;});
