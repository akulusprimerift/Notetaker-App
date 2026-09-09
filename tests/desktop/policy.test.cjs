const {test} = require('node:test');
const assert = require('node:assert/strict');
const {ORIGIN,localPage,audioPermission} = require('../../apps/desktop/policy.cjs');
const {discoverModels} = require('../../apps/desktop/models.cjs');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');

test('navigation and microphone grants remain inside the exact workspace origin',()=>{
  assert.ok(localPage(ORIGIN+'/#lecture/one'));
  for(const url of ['https://example.com','http://127.0.0.1:3001','http://127.0.0.1:3000.evil.test','file:///test','http://x:y@127.0.0.1:3000'])assert.equal(localPage(url),false);
  const contents={getURL:()=>ORIGIN};
  assert.ok(audioPermission(contents,'media',{mediaTypes:['audio'],requestingUrl:ORIGIN}));
  assert.equal(audioPermission(contents,'media',{mediaTypes:['video'],requestingUrl:ORIGIN}),false);
  assert.equal(audioPermission(contents,'media',{mediaTypes:['audio'],requestingUrl:'https://evil.test'}),false);
  assert.equal(audioPermission(contents,'geolocation',{mediaTypes:['audio']}),false);
});

test('model discovery reads installed metadata and local files without downloads',async()=>{
  const home=await fs.mkdtemp(path.join(os.tmpdir(),'notetaker-model-test-'));
  try{
    const folder=path.join(home,'.lmstudio','models','publisher','model');await fs.mkdir(folder,{recursive:true});
    await fs.writeFile(path.join(folder,'test.gguf'),'synthetic metadata fixture');
    const speech=path.join(home,'speech');await fs.mkdir(speech);await fs.writeFile(path.join(speech,'model.bin'),'fixture');await fs.writeFile(path.join(speech,'config.json'),'{}');
    const urls=[];
    const result=await discoverModels({home,speechPath:speech,fetcher:async(url)=>{urls.push(url);return{ok:true,json:async()=>({models:[{name:'installed:local',digest:'abc',size:10}]})};}});
    assert.deepEqual(urls,['http://127.0.0.1:11434/api/tags']);
    assert.equal(result.ollama[0].name,'installed:local');assert.equal(result.otherFiles.length,1);assert.equal(result.speech.path,speech);
    const offline=await discoverModels({home,fetcher:async()=>{throw new Error('offline');}});
    assert.equal(offline.ollamaAvailable,false);assert.equal(offline.otherFiles.length,1);
  }finally{assert.equal(path.dirname(path.resolve(home)),path.resolve(os.tmpdir()));assert.ok(path.basename(home).startsWith('notetaker-model-test-'));await fs.rm(home,{recursive:true,force:true});}
});
