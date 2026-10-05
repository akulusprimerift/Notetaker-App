const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const {createHash}=require('node:crypto');
const {EventEmitter}=require('node:events');
const {safeRelative,verifyBundle,NativeRuntime}=require('../../apps/desktop/native-runtime.cjs');

test('legacy library detection preserves its database and credential before any service launch',async()=>{
  const directory=await fs.mkdtemp(path.join(os.tmpdir(),'notetaker-runtime-test-'));
  try{
    const resources=path.join(directory,'bundle'),dataPath=path.join(directory,'profile'),libraryPath=path.join(dataPath,'legacy');
    await fs.mkdir(path.join(resources,'service'),{recursive:true});await fs.mkdir(path.join(libraryPath,'postgres'),{recursive:true});
    const bytes=Buffer.from('synthetic Mac service');
    await fs.writeFile(path.join(resources,'service','NotetakerService'),bytes);
    await fs.writeFile(path.join(resources,'runtime-manifest.json'),JSON.stringify({schema_version:1,platform:'darwin',arch:'arm64',profile:'macos-sqlite-local-reconciliation',
      files:[{path:'service/NotetakerService',sha256:createHash('sha256').update(bytes).digest('hex')}]}));
    const secretPath=path.join(dataPath,'standalone-secret.bin');await fs.writeFile(secretPath,'preserved encrypted credential');
    await fs.writeFile(path.join(libraryPath,'postgres/PG_VERSION'),'17');
    const runtime=new NativeRuntime({resources,dataPath,libraryPath,platform:require('../../apps/desktop/platform.cjs').desktopPlatform('darwin','arm64'),
      utilityProcess:{fork:()=>assert.fail('must not launch services')}});
    await assert.rejects(runtime.start(),/Convert.*PostgreSQL/);
    assert.equal(await fs.readFile(secretPath,'utf8'),'preserved encrypted credential');
    assert.equal(await fs.readFile(path.join(libraryPath,'postgres/PG_VERSION'),'utf8'),'17');
    assert.equal(runtime.host,null);
    await fs.unlink(path.join(libraryPath,'postgres/PG_VERSION'));
    await fs.rmdir(path.join(libraryPath,'postgres'));
    await fs.writeFile(path.join(libraryPath,'conversion.pending'),'unfinished synthetic import');
    await assert.rejects(runtime.start(),/conversion is incomplete/);
    assert.equal(runtime.host,null);
    assert.equal(await fs.readFile(path.join(libraryPath,'conversion.pending'),'utf8'),'unfinished synthetic import');
  }finally{
    assert.equal(path.dirname(path.resolve(directory)),path.resolve(os.tmpdir()));
    assert.ok(path.basename(directory).startsWith('notetaker-runtime-test-'));
    await fs.rm(directory,{recursive:true,force:true});
  }
});

test('native shutdown waits for parent-pipe cleanup and does not kill a cleanly exited host',async()=>{
  const runtime=new NativeRuntime({resources:'unused',dataPath:'unused',safeStorage:{},utilityProcess:{}});
  const host=new EventEmitter();host.exitCode=null;host.signalCode=null;
  host.kill=()=>assert.fail('clean shutdown must not force termination');
  host.stdin={end:()=>{host.exitCode=0;host.emit('exit',0);}};
  runtime.host=host;runtime.ready=true;
  await runtime.stop();
  assert.equal(runtime.host,null);assert.equal(runtime.ready,false);
  assert.equal(host.listenerCount('exit'),0);
  runtime.host=host;
  host.stdin.end=()=>assert.fail('already exited host must not receive another stop');
  await runtime.stop();
});

test('native runtime rejects paths outside its bundle',()=>{
  for(const value of ['../secret','/absolute','C:\\secret','a/../b','a\\b','a//b'])assert.throws(()=>safeRelative(value));
  assert.equal(safeRelative('service/NotetakerService.exe'),'service/NotetakerService.exe');
});
test('runtime verification catches damage before any executable starts',async()=>{
  const directory=await fs.mkdtemp(path.join(os.tmpdir(),'notetaker-runtime-test-'));
  try{
    const bytes=Buffer.from('synthetic executable');
    await fs.writeFile(path.join(directory,'service.exe'),bytes);
    await fs.writeFile(path.join(directory,'runtime-manifest.json'),JSON.stringify({schema_version:1,
      files:[{path:'service.exe',sha256:createHash('sha256').update(bytes).digest('hex')}]}));
    await verifyBundle(directory);
    await fs.writeFile(path.join(directory,'service.exe'),'damaged');
    const runtime=new NativeRuntime({resources:directory,dataPath:path.join(directory,'data'),safeStorage:{},utilityProcess:{}});
    await assert.rejects(runtime.start(),/damaged/);
    assert.equal(runtime.host,null);
  }finally{
    assert.equal(path.dirname(path.resolve(directory)),path.resolve(os.tmpdir()));
    assert.ok(path.basename(directory).startsWith('notetaker-runtime-test-'));
    await fs.rm(directory,{recursive:true,force:true});
  }
});
