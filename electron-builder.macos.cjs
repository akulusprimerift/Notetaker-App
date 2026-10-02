'use strict';
const path=require('node:path');
const {requireMac}=require('./scripts/macos-runtime.cjs');
requireMac();
if(!process.env.NOTETAKER_NATIVE_RESOURCES)throw new Error('Use bun run build:macos-app with a verified Mac runtime.');
const shared=require('./electron-builder.cjs');
// Developer ID signing when the keychain holds one (CI imports it from secrets); otherwise ad-hoc.
const developerId=process.env.NOTETAKER_MAC_SIGN==='developer-id';
const entitlements='apps/desktop/entitlements.mac.plist';
module.exports={
  ...shared,
  directories:{output:'.local/macos-standalone-dist'},
  // CFBundleVersion: CI run number so each build orders after the last.
  ...(process.env.GITHUB_RUN_NUMBER?{buildVersion:process.env.GITHUB_RUN_NUMBER}:{}),
  extraResources:shared.extraResources.filter(resource=>!resource.to.startsWith('account-client')).concat([
    {from:path.join(process.env.NOTETAKER_NATIVE_RESOURCES,'account-client'),to:'account-client'},
  ]),
  mac:{target:[{target:'dmg',arch:['arm64']}],icon:'apps/desktop/icon-mac.png',category:'public.app-category.education',
    identity:developerId?undefined:'-',hardenedRuntime:developerId,entitlements,entitlementsInherit:entitlements,
    // The runtime manifest hashes every native file; those binaries are signed before staging.
    signIgnore:['/Contents/Resources/native-runtime/'],
    notarize:developerId,
    extendInfo:{NSMicrophoneUsageDescription:'Notetaker records lecture audio only when you start recording, so it can save and transcribe your lecture.'}},
  dmg:{title:'Notetaker ${version}',format:'UDZO',writeUpdateInfo:false},
  artifactName:`Notetaker-\${version}-macOS-arm64${developerId?'':'-unsigned'}.\${ext}`,
};
