const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs/promises');
const path=require('node:path');
const os=require('node:os');
const {createHash}=require('node:crypto');
const {safeRelative,verifyBundle,NativeRuntime}=require('../../apps/desktop/native-runtime.cjs');

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
