'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');

async function validSpeechFolder(folder){
  if(!folder)return false;
  try{return (await Promise.all(['model.bin','config.json','tokenizer.json'].map(async name=>(await fs.stat(path.join(folder,name))).isFile()))).every(Boolean);}
  catch{return false;}
}

async function discoverModels({home = os.homedir(), speechPath = '', fetcher = fetch, ollamaURL = 'http://127.0.0.1:11434'} = {}) {
  const result = {ollama: [], ollamaAvailable: false, otherFiles: [], speech: null, ollamaManifests: []};
  try {
    const response = await fetcher(ollamaURL+'/api/tags', {signal: AbortSignal.timeout(3000), redirect: 'error'});
    if (response.ok) {
      const body = await response.json();
      result.ollama = (body.models || []).filter(m => typeof m.name === 'string' && !m.remote_host && !m.remote_model && !m.name.toLowerCase().includes('cloud')).map(m => ({name:m.name, size:m.size, digest:m.digest}));
      result.ollamaAvailable = true;
    }
  } catch { /* A stopped provider does not prevent recording or local file discovery. */ }
  const roots = [path.join(home, '.lmstudio', 'models'), path.join(home, '.cache', 'lm-studio', 'models'),
    path.join(home, '.cache', 'huggingface', 'hub')];
  async function scan(directory, depth = 0) {
    if (depth > 4 || result.otherFiles.length >= 100) return;
    let entries;
    try { entries = await fs.readdir(directory, {withFileTypes:true}); } catch { return; }
    for (const entry of entries.slice(0, 300)) {
      if (entry.isSymbolicLink()) continue;
      const file = path.join(directory, entry.name);
      if (entry.isDirectory()) await scan(file, depth + 1);
      else if (/\.(gguf|safetensors)$/i.test(entry.name) && result.otherFiles.length < 100)
        result.otherFiles.push({name:entry.name, path:file, status:'Detected file; not an Ollama note model selection'});
    }
  }
  await Promise.all(roots.map(root => scan(root)));
  async function manifests(directory, parts = []) {
    if (parts.length > 5 || result.ollamaManifests.length >= 100) return;
    let entries;
    try {entries=await fs.readdir(directory,{withFileTypes:true});} catch {return;}
    for (const entry of entries.slice(0,300)) {
      if(entry.isSymbolicLink())continue;
      if(entry.isDirectory())await manifests(path.join(directory,entry.name),[...parts,entry.name]);
      else if(entry.isFile())result.ollamaManifests.push([...parts,entry.name].join('/'));
    }
  }
  await manifests(path.join(home,'.ollama','models','manifests'));
  if(await validSpeechFolder(speechPath))result.speech={path:speechPath,status:'Local faster-whisper model files found; runtime compatibility still checked by the speech worker'};
  return result;
}
async function discoverSpeechModels({home=os.homedir(), roots=[], selected=''}={}) {
  const found=[];let visited=0;
  async function scan(folder,depth=0){
    if(depth>4||found.length>=20||visited++>=500)return;
    if(await validSpeechFolder(folder)){found.push(folder);return;}
    let entries;try{entries=await fs.readdir(folder,{withFileTypes:true});}catch{return;}
    for(const entry of entries.slice(0,100))if(entry.isDirectory()&&!entry.isSymbolicLink())await scan(path.join(folder,entry.name),depth+1);
  }
  if(selected)await scan(selected,4);
  for(const root of [...roots,path.join(home,'Downloads'),path.join(home,'Models'),path.join(home,'.cache','huggingface','hub')])await scan(root);
  return [...new Set(found)];
}
module.exports = {discoverModels,discoverSpeechModels,validSpeechFolder};
