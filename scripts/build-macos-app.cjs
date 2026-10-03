'use strict';
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const {requireMac,auditNative,sameInventory}=require('./macos-runtime.cjs');
const {inventory}=require('./prepare-desktop-web.cjs');
const {verifyBundle}=require('../apps/desktop/native-runtime.cjs');
const {validateRuntimeTarget,desktopPlatform}=require('../apps/desktop/platform.cjs');

async function main() {
  requireMac();
  if(process.argv.length!==3)throw new Error('Usage: bun run build:macos-app <staged-macos-runtime>');
  const root=path.resolve(__dirname,'..'),resources=path.resolve(process.argv[2]);
  const manifest=await verifyBundle(resources);
  validateRuntimeTarget(manifest,desktopPlatform());
  if(manifest.profile!=='macos-sqlite-seaweed-reconciliation')throw new Error('Expected a staged Mac standalone runtime.');
  if(!sameInventory((await inventory(resources)).filter(file=>file.path!=='runtime-manifest.json'),manifest.files))
    throw new Error('The staged Mac runtime inventory changed. Prepare a new verified bundle.');
  await auditNative(resources,manifest.files);
  const developerId=process.env.NOTETAKER_MAC_SIGN==='developer-id';
  execFileSync(process.execPath,[require.resolve('electron-builder/cli.js'),'--config','electron-builder.macos.cjs','--mac','--arm64','--publish','never'],
    {cwd:root,stdio:'inherit',env:{...process.env,NOTETAKER_NATIVE_RESOURCES:resources,CSC_IDENTITY_AUTO_DISCOVERY:developerId?'true':'false'}});
}
main().catch(error=>{console.error(error.message);process.exitCode=1;});
