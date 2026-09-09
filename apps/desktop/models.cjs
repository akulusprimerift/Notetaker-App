'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');
const os = require('node:os');

async function discoverModels({home = os.homedir(), speechPath = '', fetcher = fetch} = {}) {
  const result = {ollama: [], ollamaAvailable: false, otherFiles: [], speech: null, ollamaManifests: []};
  try {
    const response = await fetcher('http://127.0.0.1:11434/api/tags', {signal: AbortSignal.timeout(3000), redirect: 'error'});
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
  if (speechPath) {
    try {
      const stat = await fs.stat(path.join(speechPath, 'model.bin'));
      await fs.access(path.join(speechPath, 'config.json'));
      if (stat.isFile()) result.speech = {path:speechPath, status:'Local faster-whisper model files found; runtime compatibility still checked by the speech worker'};
    } catch { /* Missing models are shown explicitly. */ }
  }
  return result;
}
module.exports = {discoverModels};
