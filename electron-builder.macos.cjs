'use strict';
const path=require('node:path');
const {requireMac}=require('./scripts/macos-runtime.cjs');
requireMac();
if(!process.env.NOTETAKER_NATIVE_RESOURCES)throw new Error('Use bun run build:macos-app with a verified Mac runtime.');
const shared=require('./electron-builder.cjs');
module.exports={
  ...shared,
  directories:{output:'.local/macos-standalone-dist'},
  extraResources:shared.extraResources.filter(resource=>!resource.to.startsWith('account-client')).concat([
    {from:path.join(process.env.NOTETAKER_NATIVE_RESOURCES,'account-client'),to:'account-client'},
  ]),
  mac:{target:[{target:'dir',arch:['arm64']}],identity:null,category:'public.app-category.education',
    extendInfo:{NSMicrophoneUsageDescription:'Notetaker records lecture audio only when you start recording, so it can save and transcribe your lecture.'}},
  artifactName:'Notetaker-${version}-macOS-arm64.${ext}',
};
