'use strict';
const path=require('node:path');
const fs=require('node:fs');
const {randomUUID}=require('node:crypto');
const {execFileSync}=require('node:child_process');
const {requireMac}=require('./macos-runtime.cjs');
try {
  requireMac();
  const root=path.resolve(__dirname,'..');
  const python=path.join(root,'.venv/bin/python');
  if(!fs.existsSync(python))throw new Error('Create the locked arm64 .venv first; see the Mac runtime guide.');
  const target=execFileSync('uv',['run','--no-project','--no-sync','--python',python,'python','-c',
    'import platform, sys; print(sys.platform + "/" + platform.machine())'],{cwd:root,encoding:'utf8'}).trim();
  if(target!=='darwin/arm64')throw new Error('The service Python environment must be native macOS arm64.');
  const output=path.join(root,'.local/macos-service',randomUUID());
  execFileSync('uv',['run','--no-project','--no-sync','--python',python,'python','-m','PyInstaller',
    '--distpath',path.join(output,'dist'),'--workpath',path.join(output,'work'),
    path.join(root,'scripts/windows-service.spec')],{cwd:root,stdio:'inherit'});
  console.log('Frozen Mac service: '+path.join(output,'dist/NotetakerService'));
} catch(error) { console.error(error.message);process.exitCode=1; }
