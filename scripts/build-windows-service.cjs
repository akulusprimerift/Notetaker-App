'use strict';
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const {randomUUID}=require('node:crypto');
try {
  if(process.platform!=='win32'||process.arch!=='x64')throw new Error('Build the Windows service on Windows x64.');
  const root=path.resolve(__dirname,'..'),output=path.join(root,'.local/windows-service',randomUUID());
  execFileSync('uv',['run','--no-project','--no-sync','--python',path.join(root,'.venv/Scripts/python.exe'),'python','-m','PyInstaller',
    '--distpath',path.join(output,'dist'),'--workpath',path.join(output,'work'),path.join(root,'scripts/windows-service.spec')],
    {cwd:root,stdio:'inherit',windowsHide:true});
  console.log('Frozen Windows service: '+path.join(output,'dist/NotetakerService'));
} catch(error){console.error(error.message);process.exitCode=1;}
