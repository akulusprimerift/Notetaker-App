'use strict';
// Build-time checks only. Never discovers libraries or downloads models/runtimes.
const fs = require('node:fs/promises');
const path = require('node:path');
const {execFileSync} = require('node:child_process');
const {randomUUID} = require('node:crypto');
const {inventory} = require('./prepare-desktop-web.cjs');

const required = {
  service:['NotetakerService'],
  postgres:['bin/postgres','bin/initdb','bin/pg_ctl','share/postgresql/postgres.bki'],
  seaweed:['weed'], ollama:['ollama'], 'account-client':['bin/codex'],
};
function requireMac(platform=process.platform, arch=process.arch) {
  if(platform!=='darwin'||arch!=='arm64')throw new Error('Build on an Apple Silicon Mac with native arm64 Bun/Node and Python (not Rosetta).');
}
function inside(root, candidate) {
  const relative=path.relative(root,candidate);
  return relative===''||(!path.isAbsolute(relative)&&relative!=='..'&&!relative.startsWith('..'+path.sep));
}
async function resolvedTarget(target) {
  // Compare real paths: macOS links /var to /private/var, and the target may not exist yet.
  try { return await fs.realpath(target); } catch { return path.join(await resolvedTarget(path.dirname(target)),path.basename(target)); }
}
async function copyTree(source, destination, root=source, ancestors=[]) {
  const real=await fs.realpath(source);
  if(!ancestors.length&&inside(real,await resolvedTarget(path.resolve(destination))))throw new Error('Runtime output must be outside its source component.');
  if(!inside(root,real))throw new Error('Runtime symbolic link escapes its component: '+source);
  if(ancestors.includes(real))throw new Error('Runtime symbolic link cycle: '+source);
  const stat=await fs.stat(real);
  if(stat.isDirectory()) {
    await fs.mkdir(destination,{recursive:true});
    for(const name of await fs.readdir(real)) {
      // Model/library folders matter at a component's top level; nested code packages may use these names.
      if(name.startsWith('.env')||['.git','.local','PG_VERSION'].includes(name)||(!ancestors.length&&['models','standalone-library'].includes(name)))
        throw new Error('Private data or model directory cannot be bundled: '+name);
      await copyTree(path.join(real,name),path.join(destination,name),root,[...ancestors,real]);
    }
  } else if(stat.isFile()) {
    await fs.copyFile(real,destination);
    await fs.chmod(destination,stat.mode & 0o777);
  } else throw new Error('Unsupported runtime file: '+source);
}
function sameInventory(actual, expected) {
  if(!Array.isArray(expected)||actual.length!==expected.length)return false;
  const ordered=[...expected].sort((a,b)=>String(a.path).localeCompare(String(b.path)));
  return actual.every((file,index)=>['path','bytes','sha256'].every(key=>file[key]===ordered[index][key]));
}
function machO(bytes) {
  return bytes.length>=4&&['feedface','feedfacf','cefaedfe','cffaedfe','cafebabe','bebafeca','cafebabf','bfbafeca'].includes(bytes.subarray(0,4).toString('hex'));
}
function auditLoadPaths(output) {
  // Absolute SDK/system paths are supplied by macOS. Build-machine dependencies
  // (Homebrew, local Python, user folders) must instead be bundled/relocated.
  for(const line of output.split('\n')) {
    const reference=line.trim().match(/^(\S.*?)\s+\((?:compatibility version|offset) /)?.[1];
    if(!reference)continue;
    if(reference.startsWith('/usr/lib/')||reference.startsWith('/System/Library/'))continue;
    if(/^@(rpath|loader_path|executable_path)(\/|$)/.test(reference))continue;
    throw new Error('Non-portable Mach-O load path: '+reference);
  }
}
function auditBundledReferences(output, relative, files) {
  for(const line of output.split('\n')) {
    const reference=line.trim().match(/^(.*?)\s+\(compatibility version /)?.[1];
    if(!reference||reference.startsWith('/'))continue;
    const suffix=reference.replace(/^@[^/]+\//,'');
    if(reference.startsWith('@loader_path/')) {
      const resolved=path.posix.normalize(path.posix.join(path.posix.dirname(relative),suffix));
      if(resolved.startsWith('../')||!files.some(file=>file.path===resolved))
        throw new Error('Missing or escaping loader dependency: '+reference+' in '+relative);
    } else if(!files.some(file=>file.path===suffix||file.path.endsWith('/'+suffix))) {
      throw new Error('Missing bundled dependency: '+reference+' in '+relative);
    }
  }
}
async function auditNative(root, files, run=(command,args)=>execFileSync(command,args,{encoding:'utf8'})) {
  const native=[];
  for(const file of files) {
    const filename=path.join(root,file.path),handle=await fs.open(filename,'r');
    const header=Buffer.alloc(4);
    try{await handle.read(header,0,4,0);}finally{await handle.close();}
    if(header.subarray(0,2).toString('hex')==='4d5a'||header.toString('hex')==='7f454c46')
      throw new Error('Foreign Windows/Linux binary in Mac runtime: '+file.path);
    if(/\.(node|dylib|so)$/.test(file.path)&&!machO(header))
      throw new Error('Native library is not Mach-O: '+file.path);
    if(!machO(header))continue;
    if(!run('/usr/bin/lipo',['-archs',filename]).trim().split(/\s+/).includes('arm64'))
      throw new Error('Runtime binary lacks arm64: '+file.path);
    const dependencies=run('/usr/bin/otool',['-arch','arm64','-L',filename]);
    auditLoadPaths(dependencies);
    auditBundledReferences(dependencies,file.path,files);
    const commands=run('/usr/bin/otool',['-arch','arm64','-l',filename]);
    for(const block of commands.split(/Load command \d+/)) {
      if(/cmd LC_RPATH\s/.test(block)) {
        const rpath=block.match(/\n\s*path (.*?) \(offset \d+\)/)?.[1];
        if(!rpath)throw new Error('Unreadable Mach-O runtime search path: '+file.path);
        auditLoadPaths(rpath+' (offset 0)');
      }
    }
    native.push(file.path);
  }
  for(const [component,names] of Object.entries(required))for(const name of names.filter(name=>!name.endsWith('.bki'))) {
    const relative=component+'/'+name;
    if(!native.includes(relative))throw new Error('Required executable is not Mach-O: '+relative);
    if(!((await fs.stat(path.join(root,relative))).mode & 0o111))throw new Error('Runtime executable permission missing: '+relative);
  }
  return native;
}
async function stage({root,web,lockPath,audit=auditNative}) {
  const lock=JSON.parse(await fs.readFile(lockPath,'utf8'));
  if(lock.schema_version!==1||lock.platform!=='darwin'||lock.arch!=='arm64')throw new Error('Expected a macOS arm64 component lock.');
  for(const component of Object.keys(required)) {
    const source=lock.components?.[component];
    if(!source||typeof source.directory!=='string'||typeof source.version!=='string'||!source.version.trim()||
      typeof source.source!=='string'||!source.source.trim()||!Array.isArray(source.files)||!source.files.length)
      throw new Error('Missing component provenance/inventory: '+component);
  }
  if(!/^17\.\d+$/.test(lock.components.postgres.version))throw new Error('The standalone library requires PostgreSQL 17.');
  if(lock.components['account-client'].version!==require('../package.json').devDependencies['@openai/codex'])
    throw new Error('Account helper version must match the pinned desktop dependency.');
  const destination=path.join(root,'.local/macos-runtime',randomUUID());
  await fs.mkdir(destination,{recursive:true});
  // A failed stage remains inspectable but never receives a runtime manifest.
  const sources=[];
  for(const [component,names] of Object.entries(required)) {
    const source=lock.components[component];
    const sourceRoot=await fs.realpath(path.resolve(path.dirname(lockPath),source.directory));
    const target=path.join(destination,component);
    await copyTree(sourceRoot,target);
    const files=await inventory(target);
    if(!sameInventory(files,source.files))throw new Error('Component inventory mismatch: '+component);
    for(const name of names)if(!files.some(file=>file.path===name))throw new Error('Missing bundled file: '+component+'/'+name);
    if(!files.some(file=>/(^|\/)(license|copying|copyright|notice)([.\-_]|$)/i.test(file.path)))
      throw new Error('Include dependency license/notice files: '+component);
    sources.push({name:component,version:source.version,source:source.source,files});
  }
  await copyTree(await fs.realpath(web),path.join(destination,'web'));
  const webRoot=path.join(destination,'web');
  const webManifest=JSON.parse(await fs.readFile(path.join(webRoot,'bundle-manifest.json'),'utf8'));
  const webFiles=(await inventory(webRoot)).filter(file=>file.path!=='bundle-manifest.json');
  if(webManifest.schema_version!==1||webManifest.component!=='notetaker-desktop-web'||
    !/^[a-zA-Z0-9_-]+$/.test(webManifest.build_id)||!sameInventory(webFiles,webManifest.files))
    throw new Error('Desktop web bundle integrity check failed.');
  for(const name of ['apps/web/server.js','apps/web/.next/BUILD_ID','apps/web/public/capture/worklet.js'])
    if(!webFiles.some(file=>file.path===name))throw new Error('Incomplete desktop web bundle: '+name);
  if((await fs.readFile(path.join(webRoot,'apps/web/.next/BUILD_ID'),'utf8')).trim()!==webManifest.build_id)
    throw new Error('Desktop web build identity mismatch.');
  const files=await inventory(destination);
  const native=await audit(destination,files);
  const manifest={schema_version:1,platform:'darwin',arch:'arm64',profile:'macos-postgresql-seaweed-reconciliation',
    web_build_id:webManifest.build_id,user_models_bundled:false,speech_compute:'CPU',
    native_audit:{arm64_files:native,external_absolute_load_paths:false,native_startup_verified:false},sources,files};
  await fs.writeFile(path.join(destination,'runtime-manifest.json'),JSON.stringify(manifest,null,2)+'\n',{flag:'wx'});
  return destination;
}
async function lockComponents({root,descriptorPath}) {
  const descriptor=JSON.parse(await fs.readFile(descriptorPath,'utf8'));
  const destination=path.join(root,'.local/macos-component-locks',randomUUID());
  const components={};
  for(const name of Object.keys(required)) {
    const source=descriptor.components?.[name];
    if(!source||typeof source.directory!=='string'||typeof source.version!=='string'||!source.version.trim()||
      typeof source.source!=='string'||!source.source.trim())
      throw new Error('Declare directory, version and source for '+name);
    const directory=await fs.realpath(path.resolve(path.dirname(descriptorPath),source.directory));
    const target=path.join(destination,name);
    await copyTree(directory,target);
    components[name]={directory,version:source.version,source:source.source,files:await inventory(target)};
  }
  const lockPath=path.join(destination,'component-lock.json');
  await fs.writeFile(lockPath,JSON.stringify({schema_version:1,platform:'darwin',arch:'arm64',components},null,2)+'\n',{flag:'wx'});
  return lockPath;
}
module.exports={requireMac,copyTree,sameInventory,machO,auditLoadPaths,auditBundledReferences,auditNative,stage,lockComponents};
if(require.main===module) {
  Promise.resolve().then(()=>{
    requireMac();
    if(process.argv.length!==4)throw new Error('Usage: bun run prepare:macos-runtime <web-bundle> <component-lock.json>');
    return stage({root:path.resolve(__dirname,'..'),web:path.resolve(process.argv[2]),lockPath:path.resolve(process.argv[3])});
  }).then(destination=>console.log('Prepared Mac runtime: '+destination)).catch(error=>{console.error(error.message);process.exitCode=1;});
}
