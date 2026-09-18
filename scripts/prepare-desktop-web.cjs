'use strict';
const fs = require('node:fs/promises');
const path = require('node:path');
const {createHash, randomUUID} = require('node:crypto');
const {spawn} = require('node:child_process');

async function inventory(root, relative = '') {
  const files = [];
  for (const entry of await fs.readdir(path.join(root, relative), {withFileTypes:true})) {
    const name = path.join(relative, entry.name);
    if (entry.name.startsWith('.env') || ['.local', '.git'].includes(entry.name))
      throw new Error('Private configuration cannot be included in the web bundle.');
    if (entry.isSymbolicLink()) throw new Error('Web bundle contains an unexpected symbolic link.');
    if (entry.isDirectory()) files.push(...await inventory(root, name));
    else if (entry.isFile()) {
      const bytes = await fs.readFile(path.join(root, name));
      files.push({path:name.split(path.sep).join('/'), bytes:bytes.length,
        sha256:createHash('sha256').update(bytes).digest('hex')});
    }
  }
  return files.sort((a,b)=>a.path.localeCompare(b.path));
}

async function prepare(root) {
  const web = path.join(root, 'apps/web');
  await new Promise((resolve,reject)=>{
    const child = spawn(process.execPath, [require.resolve('next/dist/bin/next'), 'build'], {
      cwd:web, windowsHide:true, stdio:'inherit',
      env:{...process.env, NOTETAKER_WEB_BUNDLE:'1', API_ORIGIN:'http://127.0.0.1:8010', NEXT_TELEMETRY_DISABLED:'1'},
    });
    child.once('error',reject);
    child.once('exit',code=>code===0?resolve():reject(new Error('Desktop web build failed.')));
  });
  const source = path.join(web, '.next/standalone');
  // Next may copy build-time .env files; reject them before copying anything.
  await inventory(source);
  const destination = path.join(root, '.local/desktop-web', randomUUID());
  await fs.mkdir(destination, {recursive:true});
  await fs.cp(source, destination, {recursive:true});
  await fs.cp(path.join(web, '.next/static'), path.join(destination, 'apps/web/.next/static'), {recursive:true});
  await fs.cp(path.join(web, 'public'), path.join(destination, 'apps/web/public'), {recursive:true});
  const files = await inventory(destination);
  for (const required of ['apps/web/server.js', 'apps/web/.next/BUILD_ID', 'apps/web/public/capture/worklet.js']) {
    if (!files.some(file=>file.path===required)) throw new Error('Desktop web bundle is incomplete: '+required);
  }
  const manifest = {schema_version:1, component:'notetaker-desktop-web',
    entrypoint:'apps/web/server.js', host:'127.0.0.1', api_origin:'http://127.0.0.1:8010',
    node_requirement:require('../package.json').engines.node,
    next_version:require('next/package.json').version,
    build_id:(await fs.readFile(path.join(destination, 'apps/web/.next/BUILD_ID'), 'utf8')).trim(),
    runtime_bundled:false, files};
  await fs.writeFile(path.join(destination, 'bundle-manifest.json'), JSON.stringify(manifest,null,2)+'\n');
  return destination;
}

module.exports = {inventory, prepare};
if (require.main === module) prepare(path.resolve(__dirname,'..')).then(destination=>{
  console.log('Prepared desktop web bundle: '+destination);
}).catch(error=>{console.error(error.message);process.exitCode=1;});
