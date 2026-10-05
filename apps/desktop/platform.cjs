'use strict';
const path = require('node:path');

function desktopPlatform(platform=process.platform, arch=process.arch) {
  if(platform==='win32'&&arch==='x64')return {platform,arch,service:'NotetakerService.exe',
    helperPackage:'codex-win32-x64',helperVendor:'x86_64-pc-windows-msvc',helper:'codex.exe'};
  if(platform==='darwin'&&arch==='arm64')return {platform,arch,service:'NotetakerService',
    helperPackage:'codex-darwin-arm64',helperVendor:'aarch64-apple-darwin',helper:'codex'};
  throw new Error('This desktop runtime supports Windows x64 and macOS Apple Silicon only.');
}
function accountExecutable({packaged,resources,root,platform=desktopPlatform()}) {
  return packaged ? path.join(resources,'account-client','bin',platform.helper)
    : path.join(root,'node_modules','@openai',platform.helperPackage,'vendor',platform.helperVendor,'bin',platform.helper);
}
function validateRuntimeTarget(manifest, target=desktopPlatform()) {
  const platform=manifest.platform,arch=manifest.arch;
  if(platform!==target.platform||arch!==target.arch)throw new Error('The bundled runtime does not match this computer. Install the matching Notetaker build.');
  if(manifest.profile!==`${platform==='win32'?'windows':'macos'}-sqlite-local-reconciliation`)
    throw new Error('This build requires a standalone SQLite runtime. Rebuild or install the updated app.');
  if(!manifest.files.some(file=>file.path===`service/${target.service}`))throw new Error('The bundled service is missing from the runtime manifest.');
}
module.exports={desktopPlatform,accountExecutable,validateRuntimeTarget};
