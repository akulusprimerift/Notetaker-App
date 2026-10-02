const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const os=require('node:os');
const path=require('node:path');
const {spawnSync}=require('node:child_process');
const {inventory}=require('../../scripts/prepare-desktop-web.cjs');
const {requireMac,copyTree,sameInventory,auditLoadPaths,auditBundledReferences,auditNative,stage,lockComponents}=require('../../scripts/macos-runtime.cjs');
const {verifyBundle}=require('../../apps/desktop/native-runtime.cjs');
const {validateRuntimeTarget,desktopPlatform}=require('../../apps/desktop/platform.cjs');

async function temporary(run) {
  const root=await fs.mkdtemp(path.join(os.tmpdir(),'notetaker-macos-build-'));
  try { await run(root); } finally {
    assert.equal(path.dirname(path.resolve(root)),path.resolve(os.tmpdir()));
    assert.ok(path.basename(root).startsWith('notetaker-macos-build-'));
    await fs.rm(root,{recursive:true,force:true});
  }
}
async function write(root,name,bytes) {
  const filename=path.join(root,name);await fs.mkdir(path.dirname(filename),{recursive:true});
  await fs.writeFile(filename,bytes);
}
async function fixture(root) {
  const components={};
  for(const [name,paths] of Object.entries({service:['NotetakerService'],
    postgres:['bin/postgres','bin/initdb','bin/pg_ctl','share/postgresql/postgres.bki'],
    seaweed:['weed'],ollama:['ollama'],'account-client':['bin/codex']})) {
    const directory=path.join(root,'inputs',name);
    for(const file of [...paths,'LICENSE'])await write(directory,file,'synthetic '+file);
    components[name]={directory,version:name==='postgres'?'17.11':name==='account-client'?'0.154.0':'fixture-1',
      source:'synthetic fixture, never executable',files:await inventory(directory)};
  }
  const web=path.join(root,'web');
  for(const name of ['apps/web/server.js','apps/web/.next/BUILD_ID','apps/web/public/capture/worklet.js'])await write(web,name,'synthetic');
  await write(web,'bundle-manifest.json',JSON.stringify({schema_version:1,component:'notetaker-desktop-web',build_id:'synthetic',files:await inventory(web)}));
  const lock={schema_version:1,platform:'darwin',arch:'arm64',components};
  const lockPath=path.join(root,'components.json');
  const save=()=>write(root,'components.json',JSON.stringify(lock));await save();
  return {root,web,lockPath,lock,save,audit:async()=>['synthetic-audit-only']};
}

test('Mac build entrypoints reject Windows and Rosetta before writing or spawning builds',()=>{
  requireMac('darwin','arm64');
  for(const target of [['win32','x64'],['darwin','x64'],['linux','arm64']])assert.throws(()=>requireMac(...target),/Apple Silicon/);
  if(process.platform!=='darwin'||process.arch!=='arm64')for(const name of ['build-macos-service.cjs','macos-runtime.cjs','build-macos-app.cjs','lock-macos-components.cjs']) {
    const result=spawnSync(process.execPath,[path.resolve(__dirname,'../../scripts',name)],{encoding:'utf8'});
    assert.equal(result.status,1);assert.match(result.stderr,/Apple Silicon/);
  }
});
test('Mac stage produces a verified target manifest and retains every source byte',async()=>temporary(async root=>{
  const input=await fixture(root),before=await inventory(path.join(root,'inputs'));
  const generated=await lockComponents({root,descriptorPath:input.lockPath});
  // Locks record resolved directories (macOS /var is /private/var).
  for(const component of Object.values(input.lock.components))component.directory=await fs.realpath(component.directory);
  assert.deepEqual(JSON.parse(await fs.readFile(generated,'utf8')),input.lock);
  const destination=await stage(input),manifest=await verifyBundle(destination);
  validateRuntimeTarget(manifest,desktopPlatform('darwin','arm64'));
  assert.equal(manifest.user_models_bundled,false);
  assert.equal(manifest.native_audit.native_startup_verified,false);
  assert.deepEqual(await inventory(path.join(root,'inputs')),before);
  assert.equal(manifest.sources.length,5);
  await write(destination,'seaweed/weed','tampered');
  await assert.rejects(verifyBundle(destination),/damaged/);
}));
test('Mac stage refuses damaged, incomplete, unlicensed and incompatible components',async()=>temporary(async root=>{
  for(const failure of ['hash','missing','license','postgres','helper','web','audit']) {
    const input=await fixture(path.join(root,failure));
    if(failure==='hash')await write(input.lock.components.ollama.directory,'ollama','modified');
    if(failure==='missing'||failure==='license') {
      const component=input.lock.components.seaweed;
      await fs.unlink(path.join(component.directory,failure==='missing'?'weed':'LICENSE'));
      component.files=await inventory(component.directory);await input.save();
    }
    if(failure==='postgres'||failure==='helper') {
      input.lock.components[failure==='postgres'?'postgres':'account-client'].version='18.0';await input.save();
    }
    if(failure==='web')await write(input.web,'apps/web/server.js','modified');
    if(failure==='audit')input.audit=async()=>{throw new Error('native audit failure');};
    await assert.rejects(stage(input),/mismatch|Missing bundled|license|PostgreSQL 17|helper version|integrity|native audit/);
    const output=path.join(input.root,'.local/macos-runtime');
    for(const directory of await fs.readdir(output).catch(()=>[]))
      await assert.rejects(fs.access(path.join(output,directory,'runtime-manifest.json')));
  }
}));
test('runtime copy refuses private data and escaping or cyclic directory links',async()=>temporary(async root=>{
  const source=path.join(root,'source'),outside=path.join(root,'outside');
  await fs.mkdir(source);await fs.mkdir(outside);
  await assert.rejects(copyTree(source,path.join(source,'nested-copy')),/outside its source/);
  await fs.symlink(outside,path.join(source,'escape'),process.platform==='win32'?'junction':'dir');
  await assert.rejects(copyTree(source,path.join(root,'escape-copy')),/escapes/);
  await fs.unlink(path.join(source,'escape'));
  await fs.symlink(source,path.join(source,'cycle'),process.platform==='win32'?'junction':'dir');
  await assert.rejects(copyTree(source,path.join(root,'cycle-copy')),/cycle/);
  await fs.unlink(path.join(source,'cycle'));
  await write(source,'.env.private','must not ship');
  await assert.rejects(copyTree(source,path.join(root,'private-copy')),/Private/);
}));
test('Mach-O audit rejects x64-only binaries and build-machine dependencies',async()=>temporary(async root=>{
  assert.throws(()=>auditBundledReferences('@loader_path/../../outside.dylib (compatibility version 1.0.0)', 'service/main',[]),/escaping/);
  assert.throws(()=>auditBundledReferences('@rpath/missing.dylib (compatibility version 1.0.0)', 'service/main',[]),/Missing/);
  auditBundledReferences('@loader_path/lib.dylib (compatibility version 1.0.0)', 'service/main',[{path:'service/lib.dylib'}]);
  auditLoadPaths('\t/usr/lib/libSystem.B.dylib (compatibility version 1.0.0, current version 1.0.0)');
  auditLoadPaths('@loader_path (offset 12)');
  for(const name of ['/opt/homebrew/lib/libpq.dylib','/Users/build/Python','relative/lib.dylib'])
    assert.throws(()=>auditLoadPaths(name+' (compatibility version 1.0.0, current version 1.0.0)'),/Non-portable/);
  await write(root,'service/NotetakerService',Buffer.from('cffaedfe00000000','hex'));
  const files=await inventory(root);
  await assert.rejects(auditNative(root,files,()=> 'x86_64'),/lacks arm64/);
  await assert.rejects(auditNative(root,files,command=>command.endsWith('lipo')?'arm64':'\t/opt/homebrew/lib/libfoo.dylib (compatibility version 1.0.0, current version 1.0.0)'),/Non-portable/);
  await assert.rejects(auditNative(root,files,(command,args)=>command.endsWith('lipo')?'arm64':args.includes('-l')?'Load command 1\n cmd LC_RPATH\n path /Users/build/lib (offset 12)':''),/Non-portable/);
  assert.equal(sameInventory(files,[...files,{path:'extra'}]),false);
  // A dylib's own @rpath install name is not a missing dependency.
  const self=path.join(root,'self');
  await write(self,'service/libself.1.2.dylib',Buffer.from('cffaedfe00000000','hex'));
  await assert.rejects(auditNative(self,await inventory(self),(command,args)=>command.endsWith('lipo')?'arm64':
    args.includes('-D')?'libself.1.2.dylib:\n@rpath/libself.1.dylib':args.includes('-L')?'libself.1.2.dylib:\n\t@rpath/libself.1.dylib (compatibility version 1.0.0, current version 1.2.0)':''),/Required executable/);
}));
test('Mac audit rejects foreign native web modules and corrupt native libraries',async()=>temporary(async root=>{
  for(const [name,header] of [['windows.node','4d5a0000'],['linux.node','7f454c46'],['broken.dylib','00000000']]) {
    await write(root,name,Buffer.from(header,'hex'));
    await assert.rejects(auditNative(root,[{path:name}],()=>assert.fail('Foreign files must fail before calling Mac tools')),/Foreign|not Mach-O/);
  }
}));
